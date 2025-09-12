#!/usr/bin/env python3
"""
Batch evaluate /complete for code suggestions.

Usage:
  python prompt_eval.py --server-url http://127.0.0.1:9000 --input tests.jsonl --out results.csv

Optional:
  --api-key 5conmeo        Bearer token nếu server yêu cầu
  --max-tokens 120         Override server default
  --temperature 0.2        Override server default
  --timeout 60             HTTP timeout seconds
  --fail-fast              Stop at first failure (non-200)
"""

import argparse, csv, json, sys, time
from typing import Dict, Any, List, Optional
import requests

def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * p
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    d0 = values[f] * (c - k)
    d1 = values[c] * (k - f)
    return d0 + d1

def build_headers(api_key: Optional[str]) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h

def post_complete(server_url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float):
    url = server_url.rstrip("/") + "/complete"
    t0 = time.perf_counter()
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    dt = (time.perf_counter() - t0) * 1000.0
    return resp, dt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-url", required=True)
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--input", required=True, help="Path to tests.jsonl")
    ap.add_argument("--out", required=True, help="Path to results.csv")
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--fail-fast", action="store_true")
    args = ap.parse_args()

    headers = build_headers(args.api_key)

    tests: List[Dict[str, Any]] = []
    with open(args.input, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                tests.append(obj)
            except json.JSONDecodeError as e:
                print(f"[WARN] Bad JSON at line {ln}: {e}", file=sys.stderr)

    results = []
    latencies_ok = []
    ok = 0
    fail = 0

    for i, case in enumerate(tests, 1):
        cid = case.get("id", f"case_{i}")
        payload: Dict[str, Any] = {
            "prefix": case["prefix"],
            "suffix": case.get("suffix", ""),
            "language": case.get("language", "python"),
        }
        if args.max_tokens is not None:
            payload["max_tokens"] = args.max_tokens
        if args.temperature is not None:
            payload["temperature"] = args.temperature

        try:
            resp, dt_ms = post_complete(args.server_url, payload, headers, args.timeout)
        except requests.RequestException as e:
            fail += 1
            results.append({
                "id": cid,
                "status": "error",
                "http_status": "",
                "latency_ms": f"{dt_ms if 'dt_ms' in locals() else ''}",
                "tokens_out": "",
                "has_newline": "",
                "starts_with_space": "",
                "preview": "",
                "error": f"{type(e).__name__}: {e}",
                "note": case.get("note", ""),
            })
            if args.fail_fast:
                break
            continue

        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception:
                data = {"completion": resp.text}
            comp = data.get("completion", "")
            preview = comp.replace("\n", "\\n")
            results.append({
                "id": cid,
                "status": "ok",
                "http_status": str(resp.status_code),
                "latency_ms": f"{dt_ms:.2f}",
                "tokens_out": str(len(comp)),
                "has_newline": "yes" if "\n" in comp else "no",
                "starts_with_space": "yes" if comp.startswith((" ", "\t", "\n")) else "no",
                "preview": (preview[:80] + "…") if len(preview) > 80 else preview,
                "error": "",
                "note": case.get("note", ""),
            })
            ok += 1
            latencies_ok.append(dt_ms)
        else:
            results.append({
                "id": cid,
                "status": "fail",
                "http_status": str(resp.status_code),
                "latency_ms": f"{dt_ms:.2f}",
                "tokens_out": "",
                "has_newline": "",
                "starts_with_space": "",
                "preview": "",
                "error": resp.text[:200],
                "note": case.get("note", ""),
            })
            fail += 1
            if args.fail_fast:
                break

    fieldnames = ["id","status","http_status","latency_ms","tokens_out","has_newline","starts_with_space","preview","error","note"]
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow(r)

    total = ok + fail
    p50 = percentile(latencies_ok, 0.50)
    p95 = percentile(latencies_ok, 0.95)
    p99 = percentile(latencies_ok, 0.99)
    print(f"\n=== Summary ===")
    print(f"Total: {total} | OK: {ok} | Fail: {fail}")
    if latencies_ok:
        print(f"Latency ms (ok only): p50={p50:.2f}  p95={p95:.2f}  p99={p99:.2f}")
    print(f"CSV saved to: {args.out}")
    if fail > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
