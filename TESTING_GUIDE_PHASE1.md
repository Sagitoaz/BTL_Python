# 🧪 HƯỚNG DẪN TEST GIAI ĐOẠN 1

## ✅ Những gì đã hoàn thành

### 1. **Nâng cấp Postprocessing (`server/app/core/postprocess.py`)**
   - ✅ `strip_fences()`: Loại bỏ aggressive markdown fences (```, ~~~)
   - ✅ `extract_code_content()`: Extract code từ markdown blocks
   - ✅ `align_first_line()`: Cải thiện indent alignment cho nested blocks
   - ✅ `cut_overlap_tail()` & `cut_overlap_head()`: Tối ưu overlap detection
   - ✅ Added comprehensive documentation

### 2. **Cải thiện Prompt Engineering (`server/app/services/ollama.py`)**
   - ✅ Enhanced prompt với few-shot examples
   - ✅ Clear rules về không trả markdown
   - ✅ Increased context window: 2048 → 4096 tokens
   - ✅ Added top_p (0.9) và top_k (40) sampling

### 3. **Test Suite (`server/tests/test_postprocess.py`)**
   - ✅ 30+ test cases cho postprocessing functions
   - ✅ Tests cho markdown removal, indent, overlap detection
   - ✅ Integration tests cho full pipeline

### 4. **Enhanced Test Cases (`tools/tests.jsonl`)**
   - ✅ Thêm 10 test cases mới (fibonacci, nested-if, exception, etc.)
   - ✅ Thêm `note` field để document expectations
   - ✅ Total: 40 test cases covering edge cases

---

## 🚀 CÁC BƯỚC TEST

### **Bước 1: Setup Environment**

```bash
# Activate Python environment
cd /home/sagito/Desktop/BTL_Python/server
source .venv/bin/activate  # hoặc: .venv/Scripts/activate trên Windows

# Verify dependencies
pip list | grep -E "(fastapi|ollama|pytest)"

# Nếu thiếu dependencies:
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### **Bước 2: Run Unit Tests**

```bash
# Test postprocessing functions
cd /home/sagito/Desktop/BTL_Python/server
pytest tests/test_postprocess.py -v

# Expected output:
# ✅ All tests should PASS
# ✅ Test coverage ~90%+
```

**Nếu có lỗi:**
- Check import errors → verify file structure
- Check assertion errors → review implementation logic

### **Bước 3: Start Server**

```bash
# Terminal 1: Start Ollama (nếu chưa chạy)
ollama serve

# Terminal 2: Start FastAPI server
cd /home/sagito/Desktop/BTL_Python/server
./start_server.sh

# Hoặc manual:
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:9000
# INFO:     Application startup complete
```

**Verify server:**
```bash
# Test health endpoint
curl http://localhost:9000/health

# Expected: {"status":"ok",...}
```

### **Bước 4: Test Single Completion (CLI)**

```bash
# Test basic completion
cd /home/sagito/Desktop/BTL_Python
echo "def add(a, b):\n    " | python tools/cli.py \
  --server http://localhost:9000 \
  --api-key 5conmeo

# Expected output:
# ✅ Should return: "return a + b" 
# ❌ Should NOT contain: ```python or ```
```

### **Bước 5: Run Batch Evaluation**

```bash
# Backup old results
cp tools/results.csv tools/results_old.csv 2>/dev/null || true

# Run evaluation
python tools/prompt_eval.py \
  --server-url http://localhost:9000 \
  --api-key 5conmeo \
  --input tools/tests.jsonl \
  --out tools/results_new.csv \
  --timeout 60

# Expected summary:
# Total: 40 | OK: 35-40 | Fail: 0-5
# Latency p95: <8000ms (ideally <2000ms)
```

### **Bước 6: Analyze Results**

```bash
# View results
cat tools/results_new.csv | column -t -s,

# Check for markdown fences
grep -i "```" tools/results_new.csv

# Expected: NO matches (hoặc rất ít)
```

**Key metrics to check:**
- ✅ **has_newline**: Should be "yes" for most completions
- ✅ **starts_with_space**: Consistent with indent expectations
- ❌ **preview**: Should NOT contain "```python" or "```"
- ✅ **status**: Should be "ok" for 90%+ cases

### **Bước 7: Test VSCode Extension**

```bash
# Compile TypeScript
cd /home/sagito/Desktop/BTL_Python
npm run compile

# Expected: No errors
```

**Manual test trong VSCode:**
1. Press **F5** để launch Extension Development Host
2. Mở file Python mới
3. Gõ code và xem gợi ý:
   ```python
   def fibonacci(n):
       
   ```
4. **Verify:**
   - ✅ Gợi ý xuất hiện (có thể mất 1-3 giây)
   - ✅ Indent đúng (4 spaces)
   - ❌ KHÔNG có markdown ```python
   - ✅ Code có logic đúng

### **Bước 8: Compare Before/After**

```bash
# So sánh kết quả (nếu có results_old.csv)
cd /home/sagito/Desktop/BTL_Python/tools

# Count markdown fences
echo "OLD markdown rate:"
grep -c '```' results_old.csv 2>/dev/null || echo "0"

echo "NEW markdown rate:"
grep -c '```' results_new.csv

# Compare latency
echo "OLD average latency:"
awk -F',' 'NR>1 && $4 ~ /^[0-9.]+$/ {sum+=$4; count++} END {if(count>0) print sum/count}' results_old.csv

echo "NEW average latency:"
awk -F',' 'NR>1 && $4 ~ /^[0-9.]+$/ {sum+=$4; count++} END {if(count>0) print sum/count}' results_new.csv
```

---

## 📊 SUCCESS CRITERIA

| Metric | Before | Target | Check |
|--------|--------|--------|-------|
| **Markdown fence rate** | ~80% | <5% | ⬜ |
| **Test pass rate** | ~70% | >90% | ⬜ |
| **Indent accuracy** | ~60% | >85% | ⬜ |
| **Unit tests** | N/A | All pass | ⬜ |
| **Latency P95** | 8000ms | <5000ms | ⬜ |

---

## ❗ TROUBLESHOOTING

### **Issue: Import error trong pytest**
```bash
# Fix: Add app to PYTHONPATH
cd server
export PYTHONPATH=$PWD:$PYTHONPATH
pytest tests/test_postprocess.py -v
```

### **Issue: Server connection refused**
```bash
# Check if port 9000 is in use
lsof -i :9000

# Kill existing process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --host 0.0.0.0 --port 9001
```

### **Issue: Ollama not responding**
```bash
# Check Ollama status
ollama list

# Pull model if needed
ollama pull qwen2.5-coder:7b

# Restart Ollama
pkill ollama
ollama serve
```

### **Issue: High latency**
```bash
# Check Ollama GPU usage
nvidia-smi  # if using GPU

# Reduce max_tokens
# Edit tools/tests.jsonl, lower max_tokens to 64-80
```

---

## 📝 EXPECTED TEST RESULTS

### **Good Examples:**
```csv
id,status,http_status,latency_ms,preview
py-add-basic,ok,200,1234.56,    return a + b
py-fibonacci,ok,200,2345.67,    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)
```

### **Bad Examples (should NOT see):**
```csv
# ❌ BAD: Markdown fence
py-add-basic,ok,200,1234.56,```python\n    return a + b\n```

# ❌ BAD: No indent
py-add-basic,ok,200,1234.56,return a + b

# ❌ BAD: Nonsense output
py-fibonacci,ok,200,2345.67,it
```

---

## ✅ CHECKLIST KHI HOÀN THÀNH

- [ ] Unit tests pass (30+ tests)
- [ ] Server starts without errors
- [ ] CLI tool returns clean code
- [ ] Batch evaluation: >90% success
- [ ] Markdown fence rate <5%
- [ ] VSCode extension compiles
- [ ] Manual test trong VSCode works
- [ ] Results CSV analyzed
- [ ] Compare before/after metrics

---

## 🎯 NEXT STEPS

Sau khi hoàn thành test và verify improvements:

1. **Nếu tất cả tests PASS:**
   - 🎉 Giai đoạn 1 hoàn thành!
   - Report metrics cho tôi
   - Sẵn sàng cho GIAI ĐOẠN 2: Code Formatter

2. **Nếu có issues:**
   - Report lỗi cụ thể với logs
   - Tôi sẽ debug và fix
   - Re-run tests

---

## 📞 BÁO CÁO KẾT QUẢ

Sau khi test xong, hãy report cho tôi:

```
✅ Unit tests: PASS/FAIL (X/30 passed)
✅ Server health: OK/ERROR
✅ CLI test: PASS/FAIL
✅ Batch eval: X/40 OK, Y failed
✅ Markdown rate: X% (target <5%)
✅ VSCode extension: WORKS/ERROR

Issues found:
- [Mô tả issue nếu có]
```

**Hãy chạy test và báo cáo kết quả cho tôi! 🚀**
