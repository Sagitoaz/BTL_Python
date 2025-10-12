# 🧪 HƯỚNG DẪN TEST TOÀN BỘ DỰ ÁN BTL AI CODE COMPLETION

## 📋 CHECKLIST TEST CƠ BẢN (5 phút)

### 1. ✅ Kiểm tra Server Health

```powershell
# PowerShell
Invoke-RestMethod "http://100.109.118.90:9000/health"
# Expected: {"status": "ok", "model": "qwen2.5-coder:7b", ...}

# hoặc bash/cmd với curl
curl http://100.109.118.90:9000/health
```

### 2. ✅ Test CLI Tools

```powershell
# Sync completion
echo "def add(a, b):" | C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/cli.py --server http://100.109.118.90:9000 --api-key 5conmeo --strip-fence

# Stream completion (real-time)
echo "def factorial(n):" | C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/cli.py --server http://100.109.118.90:9000 --api-key 5conmeo --stream --strip-fence
```

### 3. ✅ Test Quick Scripts

```powershell
# Windows
.\scripts\quick-test.ps1

# Linux/Mac
chmod +x scripts/quick-test.sh && ./scripts/quick-test.sh
```

---

## 🔥 TEST NHANH TOÀN BỘ (1 phút)

```powershell
# Chạy demo script - test tất cả trong 1 lần
.\demo.ps1
```

**Kết quả mong đợi:**

- ✅ Health check: status "ok"
- ✅ CLI sync: trả về code completion
- ✅ CLI stream: hiển thị từng token theo thời gian thực với [req:xxxx]
- ✅ Stress test: 10 requests, QPS ~2-4, p95 < 2s

---

## 🏗️ TEST CHI TIẾT TỪNG THÀNH PHẦN

### A. 🧪 **Server Tests (Unit/Integration)**

```powershell
cd server
C:/BTL_python/BTL_Python/.venv/Scripts/python.exe -m pytest tests/ -v
```

**Kết quả:** 3 passed (health, mock completion, error handling)

### B. 🔧 **CLI Tools Tests**

#### CLI Sync Mode

```powershell
echo "def two_sum(nums, target):" | C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/cli.py --server http://100.109.118.90:9000 --api-key 5conmeo --verbose
```

#### CLI Stream Mode

```powershell
echo "class Calculator:" | C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/cli.py --server http://100.109.118.90:9000 --api-key 5conmeo --stream --verbose
```

#### CLI với File Input

```powershell
# Tạo file test
echo "def fibonacci(n):" > test_input.py
C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/cli.py --server http://100.109.118.90:9000 --api-key 5conmeo --file test_input.py
```

### C. 📊 **Stress Testing**

#### Stress Test Nhẹ

```powershell
C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/stress.py --server http://100.109.118.90:9000 --api-key 5conmeo --requests 20 --concurrency 5 --timeout 15
```

#### Stress Test Với Custom Payload

```powershell
# Tạo payload.json
@"
{
  "prefix": "def merge_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    ",
  "suffix": "\n    return merge(left, right)",
  "language": "python",
  "max_tokens": 200,
  "temperature": 0.1
}
"@ | Out-File -Encoding UTF8 payload.json

C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/stress.py --server http://100.109.118.90:9000 --api-key 5conmeo --requests 10 --concurrency 3 --payload-file payload.json
```

### D. 🎯 **Test Matrix (Multi-scenario)**

```powershell
C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/test_matrix.py
```

**Test Cases:**

- ✅ Python + Sync + Auth → 200
- ✅ Python + Stream + Auth → 200
- ✅ Python + No Auth → 401
- ✅ JavaScript + Auth → 422 (blocked by schema)
- ✅ TypeScript + Auth → 422 (blocked by schema)

### E. 📈 **Batch Evaluation**

```powershell
C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/prompt_eval.py --server-url http://100.109.118.90:9000 --api-key 5conmeo --input Tools/tests.jsonl --out results.csv --timeout 30
```

---

## 🔍 TEST ERROR SCENARIOS

### 1. Test Authentication Errors

```powershell
# Wrong API key
echo "def test():" | C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/cli.py --server http://100.109.118.90:9000 --api-key wrongkey
# Expected: HTTP 403

# No API key
echo "def test():" | C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/cli.py --server http://100.109.118.90:9000
# Expected: HTTP 401
```

### 2. Test Server Down Scenarios

```powershell
# Test với server không tồn tại
echo "def test():" | C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/cli.py --server http://nonexistent:9000 --api-key 5conmeo --timeout 3
# Expected: Connection error
```

### 3. Test Language Schema Validation

```powershell
# Test JavaScript (should fail)
C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/cli.py --server http://100.109.118.90:9000 --api-key 5conmeo --language javascript <<< "function test() {"
# Expected: HTTP 422
```

---

## 🎮 VS CODE EXTENSION TEST

### Setup Extension

1. Open VS Code in project root
2. Press F5 to run extension in Development Host
3. Configure settings:

```json
{
  "btl.serverUrl": "http://100.109.118.90:9000",
  "btl.apiKey": "5conmeo",
  "btl.enableStreaming": true,
  "btl.timeoutMs": 8000
}
```

### Test Extension

1. **Create Python file** → test.py
2. **Type code:**

```python
def two_sum(nums, target):
    # Put cursor here and wait for suggestions
```

3. **Commands:**
   - `Ctrl+Shift+P` → "BTL: Test Completion"
   - `Ctrl+Shift+P` → "BTL: Trigger Inline Suggest"

### Expected Results

- ✅ Ghost text appears with code suggestions
- ✅ Tab to accept, Esc to dismiss
- ✅ Stream mode shows suggestions appearing gradually
- ✅ Status bar shows "Testing completion with server: ..."

---

## 📊 PERFORMANCE BENCHMARKS

### Latency Targets

- **P50:** < 500ms
- **P95:** < 1500ms
- **P99:** < 2000ms

### QPS Targets

- **Single user:** 2-5 QPS
- **Concurrent (5 users):** 8-15 QPS

### Test Command

```powershell
# Performance test
C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/stress.py --server http://100.109.118.90:9000 --api-key 5conmeo --requests 100 --concurrency 10 --timeout 20 | jq '{qps_success, p95_sec, p99_sec, error_breakdown}'
```

---

## 🐛 TROUBLESHOOTING QUICK FIXES

### Issue: CLI tools fail with "ModuleNotFoundError"

```powershell
# Fix: Install missing packages
C:/BTL_python/BTL_Python/.venv/Scripts/pip install requests httpx
```

### Issue: Server returns 502 "ollama_error"

```powershell
# Fix: Check Ollama service
curl http://127.0.0.1:11434/api/tags
# If fails, restart: ollama serve
```

### Issue: CORS errors in browser

```powershell
# Fix: Set environment variable
$env:ALLOW_ORIGINS="*"
# Restart server
```

### Issue: VS Code extension not working

1. Check Developer Console (Help → Toggle Developer Tools)
2. Verify settings: `btl.serverUrl`, `btl.apiKey`
3. Test server manually: `curl http://100.109.118.90:9000/health`

---

## ✅ FULL TEST SUITE (Complete Validation)

```powershell
# 1. Server tests
cd server && C:/BTL_python/BTL_Python/.venv/Scripts/python.exe -m pytest tests/ -v

# 2. Quick functional test
.\demo.ps1

# 3. Comprehensive test matrix
C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/test_matrix.py

# 4. Performance validation
C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/stress.py --server http://100.109.118.90:9000 --api-key 5conmeo --requests 50 --concurrency 8 --timeout 15

# 5. Batch evaluation (optional)
C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/prompt_eval.py --server-url http://100.109.118.90:9000 --api-key 5conmeo --input Tools/tests.jsonl --out results.csv
```

**Pass Criteria:**

- ✅ All server tests pass (3/3)
- ✅ Demo completes without errors
- ✅ Test matrix shows 6/6 passed
- ✅ Stress test: QPS > 2, P95 < 2s, 0 failures
- ✅ Extension shows inline suggestions

---

## 🎯 ACCEPTANCE CRITERIA

| Component | Test                | Status  | Notes                       |
| --------- | ------------------- | ------- | --------------------------- |
| Server    | Unit tests          | ✅ PASS | 3/3 tests pass              |
| Server    | Health endpoint     | ✅ PASS | Returns status "ok"         |
| CLI       | Sync completion     | ✅ PASS | Returns valid code          |
| CLI       | Stream completion   | ✅ PASS | Shows incremental tokens    |
| CLI       | Error handling      | ✅ PASS | 401/422 handled properly    |
| Stress    | Performance         | ✅ PASS | QPS 2-4, P95 < 2s           |
| Scripts   | Cross-platform      | ✅ PASS | PowerShell + Bash work      |
| Extension | VS Code integration | ✅ PASS | Inline suggestions work     |
| Schema    | Language validation | ✅ PASS | Python ✅, JS/TS blocked ❌ |

**🎉 PROJECT STATUS: FULLY FUNCTIONAL ✅**

All 4 người roles completed successfully:

- **Người 1 (Backend/Infra):** ✅ Server, CORS, logging, tests
- **Người 2 (Prompt/Model):** ✅ Prompt optimization, postprocessing
- **Người 3 (Extension):** ✅ VS Code integration, streaming UX
- **Người 4 (Tools/Integration):** ✅ CLI, stress testing, CI/CD, demos
