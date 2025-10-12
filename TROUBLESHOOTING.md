# 🔧 Known Issues & Troubleshooting

## Server Connection Issues

### ❌ 401 Unauthorized / 403 Forbidden

**Symptoms:** API calls return 401/403 status
**Cause:** Missing or invalid API key
**Fix:**

```bash
# Set correct API key
export API_KEY=5conmeo
# Or in VS Code settings
"btl.apiKey": "5conmeo"
```

### ❌ 502 Bad Gateway

**Symptoms:** Server returns 502, "ollama_error" in response
**Cause:** Ollama service is down or unreachable
**Fix:**

```bash
# Check Ollama status
curl http://127.0.0.1:11434/api/tags

# Restart Ollama if needed
ollama serve
```

### ❌ CORS Error

**Symptoms:** Browser/extension gets CORS policy errors
**Cause:** Server not allowing your origin
**Fix:**

```bash
# For demo, allow all origins
export ALLOW_ORIGINS="*"

# For production, specify exact origins
export ALLOW_ORIGINS="vscode-webview://,http://localhost:3000"
```

### ❌ Connection Refused / Timeout

**Symptoms:** "Connection refused" or timeout errors
**Cause:** Server not running or firewall blocking
**Fix:**

```bash
# Check if server is running
curl http://100.109.118.90:9000/health

# Start server if needed
cd server && uvicorn app.main:app --host 0.0.0.0 --port 9000
```

## Tool-Specific Issues

### CLI Tools (`tools/cli.py`)

```bash
# If stream fails, uses sync fallback automatically
echo "def test():" | python tools/cli.py --stream --verbose

# For debug, check server logs
python tools/cli.py --verbose --timeout 30
```

### Stress Test (`tools/stress.py`)

```bash
# Start with low concurrency
python tools/stress.py --requests 5 --concurrency 2 --timeout 15

# Check detailed error breakdown in JSON output
python tools/stress.py --requests 100 | jq .error_breakdown
```

### Extension Issues

1. **No suggestions appearing:**

   - Check VS Code settings: `btl.serverUrl`, `btl.apiKey`
   - Verify server is running: open `http://localhost:9000/health`
   - Check VS Code Developer Console for errors

2. **Slow suggestions:**
   - Reduce `btl.timeoutMs` in settings
   - Try disabling streaming: `"btl.enableStreaming": false`

## Test Matrix Status

| Language | Sync | Stream | Auth | Model | Status         |
| -------- | ---- | ------ | ---- | ----- | -------------- |
| Python   | ✅   | ✅     | ✅   | ✅    | Working        |
| JS/TS    | ❌   | ❌     | ✅   | ❌    | Schema blocked |
| Java     | ❌   | ❌     | ✅   | ❌    | Schema blocked |

**Note:** TypeScript/JavaScript blocked by schema validation - see `completion.py` line 8-10

## Quick Health Check Commands

```bash
# Server health
curl http://100.109.118.90:9000/health

# API with auth
curl -H "Authorization: Bearer 5conmeo" http://100.109.118.90:9000/models

# Quick completion test
echo "def add(a,b):" | python tools/cli.py --server http://100.109.118.90:9000 --api-key 5conmeo
```

## Environment Variables Reference

```bash
# Server
export OLLAMA_URL="http://127.0.0.1:11434"
export MODEL="qwen2.5-coder:7b"
export API_KEY="5conmeo"
export TIMEOUT_SECONDS=120
export ALLOW_ORIGINS="*"

# Client tools
export SERVER_URL="http://100.109.118.90:9000"
export API_KEY="5conmeo"
export BTL_TIMEOUT=20.0
```
