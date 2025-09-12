# client_py/bridge.py
import os, sys, json, time
from typing import Any, Dict
import requests

SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:9000")
API_KEY    = os.environ.get("API_KEY", "")
# Cho phép chỉnh timeout qua env, mặc định 20s để tránh treo ngắn
TIMEOUT    = float(os.environ.get("BTL_TIMEOUT", "20.0"))

headers = {"Content-Type": "application/json"}
if API_KEY:
    headers["Authorization"] = f"Bearer {API_KEY}"

def log(msg: str):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.stderr.flush()

def _println(obj: Dict[str, Any]):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def complete(payload: Dict[str, Any]) -> Dict[str, Any]:
    url = SERVER_URL.rstrip("/") + "/complete"
    try:
        log(f"[bridge.py] POST {url} payload={payload}")
        r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        log(f"[bridge.py] status={r.status_code}")
        r.raise_for_status()
        data = r.json()
        completion = data.get("completion") or (data.get("choices") or [{}])[0].get("text", "")
        return {"ok": True, "completion": completion}
    except Exception as e:
        log(f"[bridge.py] error: {e}")
        return {"ok": False, "error": str(e)}

def main():
    log(f"[bridge.py] start SERVER_URL={SERVER_URL} API_KEY={'set' if API_KEY else 'empty'} TIMEOUT={TIMEOUT}s")
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except Exception as e:
                log(f"[bridge.py] bad JSON line: {line!r} err={e}")
                _println({"ok": False, "error": f"bad json: {e}"})
                continue

            req_id = req.get("id")
            action = req.get("action")
            payload = req.get("payload", {})

            if action == "ping":
                _println({"id": req_id, "ok": True, "pong": True, "ts": time.time()})
                continue
            if action == "complete":
                res = complete(payload)
                res["id"] = req_id
                _println(res)
                continue

            _println({"id": req_id, "ok": False, "error": f"unknown action: {action}"})
    except KeyboardInterrupt:
        log("[bridge.py] keyboard interrupt, exiting")

if __name__ == "__main__":
    main()
