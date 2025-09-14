# tools/cli.py
import os, sys, json, argparse, re, time
import requests

DEFAULT_SERVER = os.getenv("SERVER_URL", "http://127.0.0.1:9000")
DEFAULT_API_KEY = os.getenv("API_KEY", "")

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def strip_md_fence(text: str) -> str:
    m = re.search(r"```(?:\w+)?\n(.*?)```", text, re.S)
    return m.group(1) if m else text

def build_headers(api_key: str, accept: str = "application/json", extra=None) -> dict:
    h = {"Content-Type": "application/json", "Accept": accept}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    for kv in extra or []:
        if ":" in kv:
            k, v = kv.split(":", 1)
            h[k.strip()] = v.strip()
    return h

def coalesce_completion(obj: dict) -> str:
    if not isinstance(obj, dict):
        return ""
    return (
        obj.get("completion")
        or obj.get("text")
        or (obj.get("choices", [{}])[0] or {}).get("text")
        or ((obj.get("choices", [{}])[0] or {}).get("message") or {}).get("content")
        or ""
    )

def post_complete(server: str, api_key: str, payload: dict, timeout: int, retries=0, retry_wait=0.5) -> str:
    url = server.rstrip("/") + "/complete"
    headers = build_headers(api_key, accept="application/json")
    last_err = None
    for i in range(retries + 1):
        try:
            with requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout) as r:
                if r.status_code != 200:
                    raise RuntimeError(f"[HTTP {r.status_code}] {r.text}")
                try:
                    return coalesce_completion(r.json())
                except Exception:
                    raise RuntimeError(f"Invalid JSON response: {r.text[:500]}")
        except Exception as e:
            last_err = e
            if i < retries:
                time.sleep(retry_wait * (2 ** i))
            else:
                raise SystemExit(str(last_err))

def stream_complete(server: str, api_key: str, payload: dict, timeout: int):
    base = server.rstrip("/")

    # 1) Thử SSE /complete_stream
    url_sse = base + "/complete_stream"
    headers_sse = build_headers(api_key, accept="text/event-stream")
    try:
        with requests.post(url_sse, headers=headers_sse, data=json.dumps(payload), stream=True, timeout=timeout) as r:
            if r.status_code == 200:
                current_event = None
                for line in r.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if line.startswith("event:"):
                        current_event = line.split(":", 1)[1].strip()
                        continue
                    if line.startswith("data:"):
                        raw = line[5:].strip()
                    else:
                        raw = line.strip()
                    try:
                        obj = json.loads(raw)
                        if current_event == "meta" and "request_id" in obj:
                            print(f"[req:{obj['request_id']}] ", file=sys.stderr)
                            continue
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
                raise SystemExit(f"[HTTP {r.status_code}] {r.text}")
    except requests.RequestException:
        # nếu kết nối SSE lỗi, fallback JSONL
        pass

    # 2) Fallback JSON lines: POST /complete với {"stream": true}
    url_jsonl = base + "/complete"
    headers_jsonl = build_headers(api_key, accept="application/json")
    payload2 = dict(payload); payload2["stream"] = True
    with requests.post(url_jsonl, headers=headers_jsonl, data=json.dumps(payload2), stream=True, timeout=timeout) as r2:
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

def main():
    p = argparse.ArgumentParser(description="CLI test /complete (sync/stream). Prefix đọc từ stdin hoặc file.")
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--api-key", default=DEFAULT_API_KEY)
    p.add_argument("--language", default="python")
    p.add_argument("--suffix", default="\n")
    p.add_argument("--max-tokens", type=int, default=64)
    p.add_argument("--temp", type=float, default=None)
    p.add_argument("--stream", action="store_true")
    p.add_argument("--strip-fence", action="store_true")
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--extra-header", action="append")
    p.add_argument("--file")
    p.add_argument("--suffix-file")
    p.add_argument("--retries", type=int, default=0)
    p.add_argument("--retry-wait", type=float, default=0.5)
    args = p.parse_args()

    prefix = read_text(args.file) if args.file else sys.stdin.read()
    if not prefix:
        print("stdin trống. Ví dụ: echo \"def add(a,b):\\n    \" | python tools/cli.py --stream", file=sys.stderr)
        sys.exit(1)
    if args.suffix_file:
        args.suffix = read_text(args.suffix_file)

    payload = {"prefix": prefix, "suffix": args.suffix, "language": args.language, "max_tokens": args.max_tokens}
    if args.temp is not None:
        payload["temperature"] = args.temp
    if args.verbose:
        print(f"[payload] {json.dumps(payload, ensure_ascii=False)}", file=sys.stderr)

    if args.stream:
        stream_complete(args.server, args.api_key, payload, timeout=args.timeout)
    else:
        out = post_complete(args.server, args.api_key, payload, timeout=args.timeout, retries=args.retries, retry_wait=args.retry_wait)
        print(strip_md_fence(out) if args.strip_fence else out, end="")

if __name__ == "__main__":
    main()
