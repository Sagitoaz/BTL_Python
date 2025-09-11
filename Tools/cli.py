# Tools/cli.py
# ------------------------------------------------------------
# CLI tối giản để test API hoàn thành mã:
# - Non-stream: đọc stdin -> POST /complete -> in completion
# - Stream:     đọc stdin -> POST /complete_stream (hoặc /complete?stream=true) -> in dần delta
# ------------------------------------------------------------

import os
import sys
import json
import argparse
import re
from turtle import setx
import requests



# Hàm loại bỏ code fence markdown nếu có trong output của model
# Trả về phần code bên trong fence hoặc nguyên văn nếu không có fence
def strip_md_fence(text: str) -> str:
    """
    Nếu model trả về kèm code fence Markdown ```python ... ```, hàm này sẽ lấy phần code bên trong.
    Không ảnh hưởng nếu output không có fence.
    """
    m = re.search(r"```(?:\w+)?\n(.*?)```", text, re.S)
    return m.group(1) if m else text


# Hàm xây dựng header cho request, thêm Authorization nếu có api_key
# build_headers – bồi thêm extra headers
def build_headers(api_key: str, accept: str = "application/json", extra=None) -> dict:
    h = {"Content-Type": "application/json", "Accept": accept}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    for kv in (extra or []):
        if ":" in kv:
            k, v = kv.split(":", 1)
            h[k.strip()] = v.strip()
    return h


# Hàm chuẩn hoá response từ API, lấy completion/text/choices[0].text/... tuỳ kiểu trả về
def coalesce_completion(obj: dict) -> str:
    """
    Chuẩn hoá nhiều kiểu response khác nhau.
    Ưu tiên: completion -> text -> choices[0].text -> choices[0].message.content
    """
    if not isinstance(obj, dict):
        return ""
    return (
        obj.get("completion")
        or obj.get("text")
        or (obj.get("choices", [{}])[0] or {}).get("text")
        or ((obj.get("choices", [{}])[0] or {}).get("message") or {}).get("content")
        or ""
    )


# Hàm gửi POST /complete, trả về completion đã chuẩn hoá
def post_complete(server: str, api_key: str, payload: dict, timeout: int) -> str:
    url = server.rstrip("/") + "/complete"
    headers = build_headers(api_key, accept="application/json")
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
    if r.status_code != 200:
        raise SystemExit(f"[HTTP {r.status_code}] {r.text}")
    try:
        data = r.json()
    except Exception:
        raise SystemExit(f"Invalid JSON response: {r.text[:500]}")
    return coalesce_completion(data)


# Hàm stream completion từ server, thử SSE trước, nếu không được thì fallback sang JSON lines
# In dần từng phần delta/text/content ra stdout
def stream_complete(server: str, api_key: str, payload: dict, timeout: int):
    """
    Stream linh hoạt:
      1) Thử SSE qua /complete_stream  (mỗi dòng thường có tiền tố 'data: ')
      2) Nếu 404, fallback sang /complete với {"stream": true} (thường là JSON lines)
    Cả hai trường hợp đều tự cố gắng parse JSON và in trường delta/text/content.
    """
    base = server.rstrip("/")

    # --- THỬ SSE QUA /complete_STREAM ---
    url_sse = base + "/complete_stream"
    headers_sse = build_headers(api_key, accept="text/event-stream")
    r = requests.post(url_sse, headers=headers_sse, data=json.dumps(payload), stream=True, timeout=timeout)

    if r.status_code == 200:
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            # Chuẩn SSE: "data: {...}"
            if line.startswith("data:"):
                raw = line[len("data:"):].strip()
            else:
                raw = line.strip()

            # Thử parse JSON -> lấy delta/text/content | nếu không được thì in thẳng
            try:
                obj = json.loads(raw)
                delta = (
                    obj.get("delta")
                    or obj.get("text")
                    or obj.get("content")
                    or (obj.get("choices", [{}])[0].get("delta", {}) or {}).get("content")
                    or ""
                )
                print(delta if delta is not None else "", end="", flush=True)
            except Exception:
                print(raw, end="", flush=True)
        print()
        return
    elif r.status_code != 404:
        # Nếu lỗi khác 404 thì dừng luôn
        raise SystemExit(f"[HTTP {r.status_code}] {r.text}")

    # --- FALLBACK: /complete với stream=true (JSON lines) ---
    url_jsonl = base + "/complete"
    headers_jsonl = build_headers(api_key, accept="application/json")
    payload2 = dict(payload)
    payload2["stream"] = True

    r2 = requests.post(url_jsonl, headers=headers_jsonl, data=json.dumps(payload2), stream=True, timeout=timeout)
    if r2.status_code != 200:
        raise SystemExit(f"[HTTP {r2.status_code}] {r2.text}")

    for line in r2.iter_lines(decode_unicode=True):
        if not line:
            continue
        raw = line.strip()
        try:
            obj = json.loads(raw)
            delta = (
                obj.get("delta")
                or obj.get("text")
                or obj.get("content")
                or (obj.get("choices", [{}])[0].get("delta", {}) or {}).get("content")
                or ""
            )
            print(delta if delta is not None else "", end="", flush=True)
        except Exception:
            print(raw, end="", flush=True)
    print()


# Hàm main: parse argument, đọc stdin, tạo payload, gọi API tương ứng
def main():
    p = argparse.ArgumentParser(
        description="Đọc prefix từ stdin, gọi /complete hoặc stream để in completion/delta."
    )
    # Định nghĩa các argument dòng lệnh
    p.add_argument("--server", default="http://100.109.118.90:9000",
                   help="URL server FastAPI (mặc định: %(default)s hoặc từ env SERVER_URL)")
    p.add_argument("--api-key", default="5conmeo",
                   help="Bearer token (mặc định lấy từ env API_KEY nếu có)")
    p.add_argument("--language", default="python",
                   help="Ngôn ngữ nguồn (vd: python)")
    p.add_argument("--suffix", default="\n",
                   help="Suffix ghép sau prefix (mặc định: xuống dòng)")
    p.add_argument("--max-tokens", type=int, default=64,
                   help="Giới hạn token sinh")
    p.add_argument("--temp", type=float, default=None,
                   help="Nhiệt độ (nếu server hỗ trợ)")
    p.add_argument("--stream", action="store_true",
                   help="Dùng stream để in dần delta (SSE/JSONL đều hỗ trợ)")
    p.add_argument("--strip-fence", action="store_true",
                   help="Loại bỏ Markdown code fence khỏi output khi non-stream")
    p.add_argument("--timeout", type=int, default=600,
                   help="Timeout (giây)")
    p.add_argument("--verbose", action="store_true",
                   help="In payload gửi đi (debug)")
    # argparse – thêm vài flag
    p.add_argument("--model")
    p.add_argument("--top-p", type=float)
    p.add_argument("--stop", action="append")
    p.add_argument("--n", type=int)
    p.add_argument("--seed", type=int)
    p.add_argument("--metadata", help="JSON string")
    p.add_argument("--extra-header", action="append", help="Key: Value")
    p.add_argument("--insecure", action="store_true")
    p.add_argument("--retries", type=int, default=0)
    p.add_argument("--retry-wait", type=float, default=0.5)
    p.add_argument("--file")
    p.add_argument("--suffix-file")
    p.add_argument("--raw-stream", action="store_true")
    p.add_argument("--out", default="text")  # text|json|file=PATH


    args = p.parse_args()

    # Đọc toàn bộ stdin làm prefix (mã nguồn đầu vào)
    prefix = sys.stdin.read()
    if not prefix:
        print("⚠️  stdin trống. Ví dụ:\n  'def add(a,b):`n    ' | python Tools\\cli.py --server http://host:9000 --api-key TOKEN --language python",
              file=sys.stderr)
        sys.exit(1)

    # Tạo payload gửi lên server
    payload = {
        "prefix": prefix,
        "suffix": args.suffix,
        "language": args.language,
        "max_tokens": args.max_tokens,
    }
    if args.temp is not None:
        payload["temperature"] = args.temp

    if args.verbose:
        print(f"[payload] {json.dumps(payload, ensure_ascii=False)}", file=sys.stderr)

    try:
        if args.stream:
            # Nếu chọn stream thì gọi stream_complete
            stream_complete(args.server, args.api_key, payload, timeout=args.timeout)
        else:
            # Nếu không stream thì gọi post_complete, có thể loại bỏ code fence nếu cần
            out = post_complete(args.server, args.api_key, payload, timeout=args.timeout)
            if args.strip_fence:
                out = strip_md_fence(out)
            print(out, end="")
    except KeyboardInterrupt:
        pass


# Chạy hàm main nếu chạy trực tiếp file này
if __name__ == "__main__":
    main()
