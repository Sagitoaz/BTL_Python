# 🚀 QUICK START - Phase 1 Testing

## ⚡ 5-Minute Quick Test

```bash
# 1. Start Server (Terminal 1)
cd ~/Desktop/BTL_Python/server
source .venv/bin/activate  # or .venv/Scripts/activate on Windows
./start_server.sh

# 2. Quick Unit Test (Terminal 2)
cd ~/Desktop/BTL_Python/server
source .venv/bin/activate
pytest tests/test_postprocess.py -v --tb=short

# 3. Single Completion Test
cd ~/Desktop/BTL_Python
echo "def add(a, b):\n    " | python3 tools/cli.py \
  --server http://localhost:9000 --api-key 5conmeo

# 4. Batch Test (if time permits)
python3 tools/prompt_eval.py \
  --server-url http://localhost:9000 \
  --api-key 5conmeo \
  --input tools/tests.jsonl \
  --out tools/results.csv
```

---

## ✅ What to Look For

### ✅ GOOD Signs:
- ✅ No `\`\`\`python` or `\`\`\`` in output
- ✅ Correct indentation (4 spaces for function body)
- ✅ Relevant code completions
- ✅ Tests pass without errors

### ❌ BAD Signs:
- ❌ Markdown fences in output
- ❌ No indentation or wrong indent
- ❌ Nonsense completions like "it"
- ❌ Import errors or crashes

---

## 📊 Quick Metrics Check

```bash
# Check markdown fence rate
grep -c '```' tools/results.csv

# Check success rate
awk -F',' 'NR>1 && $2=="ok" {ok++} NR>1 {total++} END {print ok"/"total" OK ("int(ok/total*100)"%)"}' tools/results.csv

# Check average latency
awk -F',' 'NR>1 && $4 ~ /^[0-9.]+$/ {sum+=$4; count++} END {print "Avg: "sum/count" ms"}' tools/results.csv
```

---

## 🎯 Success Criteria (Phase 1)

- [x] Code compiles without syntax errors ✓
- [ ] Unit tests: >27/30 pass (90%+)
- [ ] Batch eval: >35/40 OK (87%+)
- [ ] Markdown rate: <5%
- [ ] Server stable: No crashes
- [ ] VSCode extension compiles

---

## 🐛 Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: app` | `export PYTHONPATH=$PWD:$PYTHONPATH` |
| Port 9000 in use | `lsof -i :9000` then `kill -9 <PID>` |
| Ollama not responding | `ollama serve` |
| High latency | Check GPU with `nvidia-smi` |

---

## 📞 Report Format

```
✅ PHASE 1 TEST RESULTS
======================
Date: [DATE]
Tester: [YOUR NAME]

Unit Tests:     [X/30] PASS
Batch Eval:     [X/40] OK
Markdown Rate:  [X]%
Avg Latency:    [X]ms
VSCode:         [WORKS/ERROR]

Issues:
- [List any problems]

Ready for Phase 2: [YES/NO]
```

---

## 📚 Full Documentation

- **Complete Guide**: `TESTING_GUIDE_PHASE1.md`
- **Summary**: `PHASE1_SUMMARY.md`
- **Roadmap**: `IMPROVEMENT_ROADMAP.md`
- **Changes**: `CHANGELOG.md`

---

**Time Estimate:** 5-15 minutes  
**Next Phase:** Code Formatter Integration (after approval)
