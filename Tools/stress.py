# tools/stress.py
# ------------------------------------------------------------
# Stress tester cho API /complete (hoặc endpoint bất kỳ)
# - Giữ concurrency ổn định bằng asyncio.Semaphore
# - Đo QPS thành công & tổng, p95/p99
# - Phân loại lỗi: CONNECTION / TIMEOUT / HTTP_xxx / OTHER
# - Hỗ trợ --timeout / --endpoint / --payload-file
# - Đọc mặc định SERVER_URL, API_KEY từ biến môi trường
# ------------------------------------------------------------

import os
import asyncio
import argparse
import time
import json
from collections import Counter
from typing import Any, Dict, List, Tuple, Union

import httpx

ErrorItem = Tuple[Union[int, str], float]  # (status_code_or_message, elapsed_sec)


def load_payload(payload_file: str | None) -> Dict[str, Any]:
    if payload_file:
        with open(payload_file, "r", encoding="utf-8") as f:
            return json.load(f)
    # Payload tối giản để loại trừ yếu tố prompt nặng khi debug kết nối
    return {
        "prefix": "x",
        "suffix": "",
        "language": "python",
        "max_tokens": 8
    }


def percentile(sorted_list: List[float], p: int | float) -> float | None:
    if not sorted_list:
        return None
    if p <= 0:
        return sorted_list[0]
    if p >= 100:
        return sorted_list[-1]
    k = int(len(sorted_list) * float(p) / 100.0)
    if k >= len(sorted_list):
        k = len(sorted_list) - 1
    return sorted_list[k]


async def one_request(
    client: httpx.AsyncClient,
    url: str,
    api_key: str,
    payload: Dict[str, Any],
) -> tuple[bool, float, Union[int, str]]:
    """Gửi 1 request, trả (success, elapsed, status_or_msg)."""
    start = time.perf_counter()
    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        resp = await client.post(url, headers=headers, json=payload)
        elapsed = time.perf_counter() - start

        if resp.status_code == 200:
            return True, elapsed, 200
        return False, elapsed, resp.status_code

    except Exception as e:
        elapsed = time.perf_counter() - start
        return False, elapsed, str(e)


async def worker_loop(
    sem: asyncio.Semaphore,
    client: httpx.AsyncClient,
    url: str,
    api_key: str,
    payload: Dict[str, Any],
    results: List[float],
    errors: List[ErrorItem],
    idx: int,
):
    # mỗi task sẽ chờ tới lượt theo semaphore -> giữ concurrency ổn định
    async with sem:
        ok, elapsed, status = await one_request(client, url, api_key, payload)
        if ok:
            results.append(elapsed)
        else:
            errors.append((status, elapsed))


def classify_error(err: ErrorItem) -> str:
    code_or_msg, _ = err
    if isinstance(code_or_msg, int):
        return f"HTTP_{code_or_msg}"
    msg = str(code_or_msg).lower()
    if "timeout" in msg or "read timed out" in msg:
        return "TIMEOUT"
    if "refused" in msg or "10061" in msg or "connect" in msg:
        return "CONNECTION"
    if "name or service not known" in msg or "getaddrinfo failed" in msg or "dns" in msg:
        return "DNS"
    return "OTHER"


async def stress_test(
    server_url: str,
    endpoint: str,
    api_key: str,
    concurrency: int,
    total_requests: int,
    timeout: float,
    payload: Dict[str, Any],
) -> tuple[List[float], List[ErrorItem], float]:
    url = f"{server_url.rstrip('/')}{endpoint}"

    results: List[float] = []
    errors: List[ErrorItem] = []

    # httpx timeout: có thể là float hoặc object; ở đây dùng per-request timeout chung
    async with httpx.AsyncClient(timeout=timeout) as client:
        sem = asyncio.Semaphore(concurrency)

        start = time.perf_counter()
        tasks = [
            asyncio.create_task(
                worker_loop(sem, client, url, api_key, payload, results, errors, i)
            )
            for i in range(total_requests)
        ]
        # chạy tất cả task; semaphore đảm bảo chỉ có 'concurrency' task hoạt động đồng thời
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start

    return results, errors, total_time


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Simple stress tester for code-completion API")
    p.add_argument("--server", default=os.getenv("SERVER_URL", "http://100.109.118.90:9000"), help="VD: http://host:9000 (mặc định lấy từ ENV SERVER_URL)")
    p.add_argument("--endpoint", default="/complete", help="Endpoint cần test, ví dụ: /complete")
    p.add_argument("--api-key", default=os.getenv("API_KEY", "5conmeo"), help="Bearer token (mặc định lấy từ ENV API_KEY)")
    p.add_argument("--concurrency", type=int, default=10, help="Số request song song")
    p.add_argument("--requests", type=int, default=100, help="Tổng số request")
    p.add_argument("--timeout", type=float, default=10.0, help="Timeout mỗi request (giây)")
    p.add_argument("--payload-file", default="", help="Đường dẫn file JSON payload để override payload mặc định")
    return p


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    if not args.server:
        raise SystemExit("Thiếu --server và không thấy SERVER_URL trong ENV. Hãy truyền --server hoặc set ENV SERVER_URL.")

    payload = load_payload(args.payload_file or None)

    results, errors, total_time = asyncio.run(
        stress_test(
            server_url=args.server,
            endpoint=args.endpoint,
            api_key=args.api_key,
            concurrency=args.concurrency,
            total_requests=args.requests,
            timeout=args.timeout,
            payload=payload,
        )
    )

    success = len(results)
    fail = len(errors)

    qps_success = success / total_time if total_time > 0 else 0.0
    qps_total = (success + fail) / total_time if total_time > 0 else 0.0

    # breakdown lỗi
    err_types = Counter(classify_error(e) for e in errors)

    results_sorted = sorted(results)
    p95 = percentile(results_sorted, 95)
    p99 = percentile(results_sorted, 99)

    summary = {
        "server": args.server,
        "endpoint": args.endpoint,
        "timeout_sec": args.timeout,
        "total_requests": args.requests,
        "success": success,
        "fail": fail,
        "qps_success": qps_success,
        "qps_total": qps_total,
        "p95_sec": p95,
        "p99_sec": p99,
        "error_breakdown": err_types,
        "error_samples": errors[:5],
        "total_time_sec": total_time,
    }

    # In JSON để tiện redirect ra file
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
