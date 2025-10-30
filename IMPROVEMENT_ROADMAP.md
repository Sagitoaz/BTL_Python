# 🚀 KẾ HOẠCH HOÀN THIỆN DỰ ÁN AI CODE COMPLETION

## 📋 TỔNG QUAN DỰ ÁN

**Mục tiêu:** Xây dựng VSCode Extension gợi ý code AI tương tự GitHub Copilot

**Kiến trúc hiện tại:**
- **Backend:** FastAPI server + Ollama (qwen2.5-coder:7b)
- **Frontend:** VSCode Extension (TypeScript)
- **Model:** Local LLM qua Ollama API

---

## 🔴 CÁC VẤN ĐỀ HIỆN TẠI

### 1. **Chất lượng gợi ý code chưa chuẩn xác**
   - ❌ Model thường trả về markdown fence (```python```)
   - ❌ Gợi ý thiếu context (ví dụ: chỉ trả về "it")
   - ❌ Code bị lặp lại với prefix/suffix
   - ❌ Indent không đúng với code hiện tại
   - ❌ Latency cao (P95 > 8000ms)

### 2. **Code gợi ý không tự động format**
   - ❌ Không có integration với formatter (black, autopep8)
   - ❌ Không tuân thủ style guide của project
   - ❌ Whitespace và indentation không consistent

### 3. **Thiếu hệ thống thu thập dữ liệu người dùng**
   - ❌ Không log code được chấp nhận/từ chối
   - ❌ Không có feedback loop để cải thiện model
   - ❌ Không track metrics về chất lượng gợi ý

### 4. **Thiếu tính năng nâng cao**
   - ❌ Chưa có multi-line completion thông minh
   - ❌ Chưa có context từ các file khác trong project
   - ❌ Chưa có fine-tuning với dataset riêng

---

## 🎯 KẾ HOẠCH THỰC HIỆN (7 GIAI ĐOẠN)

### ✅ **GIAI ĐOẠN 1: Cải thiện Postprocessing & Prompt** (Ngày 1-2)
**Mục tiêu:** Fix ngay các lỗi cơ bản về format output

#### **Task 1.1: Nâng cấp Postprocessing Pipeline**
- Cải thiện `server/app/core/postprocess.py`
- Loại bỏ hoàn toàn markdown fences
- Fix indent alignment
- Xử lý overlap với prefix/suffix tốt hơn

#### **Task 1.2: Tối ưu Prompt Engineering**
- Cải thiện `server/app/services/ollama.py`
- Thêm ví dụ few-shot vào prompt
- Làm rõ yêu cầu không trả về markdown
- Tăng context window

#### **Task 1.3: Testing**
```bash
# Test với prompt_eval.py
python tools/prompt_eval.py --server-url http://127.0.0.1:9000 \
  --api-key 5conmeo --input tools/tests.jsonl --out tools/results_v2.csv
```

**Kỳ vọng:** 
- ✓ 0% markdown fences trong output
- ✓ Indent chính xác 95%+ cases
- ✓ Không lặp code với prefix/suffix

---

### ✅ **GIAI ĐOẠN 2: Tích hợp Code Formatter** (Ngày 2-3)

#### **Task 2.1: Thêm Black formatter vào Backend**
- Install dependencies: `black`, `autopep8`
- Tạo module `server/app/core/formatter.py`
- Integrate vào completion pipeline

#### **Task 2.2: Auto-format trong Extension**
- Đọc VSCode formatter settings
- Apply format sau khi nhận completion
- Preserve user's style preferences

#### **Task 2.3: Testing**
```bash
# Test format quality
python -m pytest server/tests/test_formatter.py -v
```

**Kỳ vọng:**
- ✓ Code output tuân thủ PEP 8
- ✓ Tự động format với black/autopep8
- ✓ Respect project .editorconfig

---

### ✅ **GIAI ĐOẠN 3: Thu thập Dataset từ User** (Ngày 3-4)

#### **Task 3.1: Logging System**
- Tạo `server/app/core/telemetry.py`
- Log mọi completion request + response
- Track user acceptance (accepted/rejected)

#### **Task 3.2: Data Storage**
- Setup SQLite/PostgreSQL database
- Schema: prefix, suffix, completion, accepted, timestamp, user_id
- API endpoint: POST `/feedback`

#### **Task 3.3: Extension Integration**
- Track khi user accept suggestion (Tab/Enter)
- Track khi user reject (Escape/continue typing)
- Gửi feedback về server

#### **Task 3.4: Export Dataset**
```bash
# Export collected data
python tools/export_dataset.py --output dataset/user_data.jsonl --format jsonl
```

**Kỳ vọng:**
- ✓ Log 100% completions
- ✓ Track acceptance rate
- ✓ Export dataset định kỳ

---

### ✅ **GIAI ĐOẠN 4: Context-Aware Completion** (Ngày 4-5)

#### **Task 4.1: Project Context Analyzer**
- Scan imports trong file hiện tại
- Parse class/function definitions
- Extract type hints và docstrings

#### **Task 4.2: Multi-file Context**
- Đọc các file liên quan trong project
- Semantic search trên codebase
- Thêm relevant snippets vào prompt

#### **Task 4.3: Caching & Performance**
- Cache parsed AST của files
- Debounce completion requests
- Giảm latency xuống <500ms

**Kỳ vọng:**
- ✓ Completion có context từ toàn project
- ✓ Latency P95 < 500ms
- ✓ Hiểu được imports và dependencies

---

### ✅ **GIAI ĐOẠN 5: Model Fine-tuning** (Ngày 5-6)

#### **Task 5.1: Dataset Preparation**
- Clean và dedupe data từ telemetry
- Filter chỉ lấy accepted completions
- Format theo Ollama training format

#### **Task 5.2: Fine-tune qwen2.5-coder**
```bash
# Fine-tune với Ollama
ollama create custom-coder -f Modelfile
```

#### **Task 5.3: A/B Testing**
- Deploy 2 models: base vs fine-tuned
- Compare acceptance rate
- Track quality metrics

**Kỳ vọng:**
- ✓ Model tùy chỉnh cho coding style của user
- ✓ Tăng acceptance rate 20%+
- ✓ Giảm latency thêm 10-15%

---

### ✅ **GIAI ĐOẠN 6: Advanced Features** (Ngày 6-7)

#### **Task 6.1: Multi-line Intelligent Completion**
- Detect khi cần complete function body
- Generate full implementation
- Smart indentation cho nested blocks

#### **Task 6.2: Code Explanation & Docs**
- Command: "Explain this code"
- Auto-generate docstrings
- Suggest type hints

#### **Task 6.3: Refactoring Suggestions**
- Detect code smells
- Suggest improvements
- Quick fix actions

**Kỳ vọng:**
- ✓ Complete toàn bộ function body
- ✓ Generate docstrings tự động
- ✓ Refactoring suggestions hữu ích

---

### ✅ **GIAI ĐOẠN 7: Polish & Optimization** (Ngày 7)

#### **Task 7.1: Performance Optimization**
- Profile và optimize slow paths
- Reduce memory usage
- Batch processing cho multiple requests

#### **Task 7.2: Error Handling & UX**
- Graceful fallback khi server down
- Loading indicators
- Clear error messages

#### **Task 7.3: Documentation & Demo**
- Video demo chức năng
- Usage guide cho users
- Developer documentation

**Kỳ vọng:**
- ✓ Stable production-ready extension
- ✓ Good UX với clear feedback
- ✓ Complete documentation

---

## 📊 SUCCESS METRICS

| Metric | Current | Target |
|--------|---------|--------|
| Markdown fence rate | 80% | 0% |
| Latency P95 | 8000ms | <500ms |
| Acceptance rate | ~30% | >60% |
| Context accuracy | Low | High |
| Format compliance | ~40% | 95%+ |

---

## 🛠️ TECH STACK UPDATES

### Backend Dependencies
```txt
# Thêm vào server/requirements.txt
black==24.1.0
autopep8==2.0.4
sqlalchemy==2.0.25
psycopg2-binary==2.9.9  # hoặc sqlite3
tree-sitter==0.21.0
tree-sitter-python==0.21.0
```

### Frontend Dependencies
```json
// Thêm vào package.json
{
  "dependencies": {
    "axios": "^1.11.0",
    "@types/uuid": "^9.0.0",
    "uuid": "^9.0.0"
  }
}
```

---

## 📝 GHI CHÚ QUAN TRỌNG

### Sau mỗi giai đoạn:
1. ✅ Run tests để verify changes
2. 📊 Review metrics improvement
3. 🧪 Manual testing với real use cases
4. 📝 Update documentation
5. 💬 Demo và xin feedback trước khi tiếp tục

### Testing Commands
```bash
# Backend tests
cd server
pytest tests/ -v --cov=app

# Frontend compile
npm run compile

# Manual testing
# 1. Start server: cd server && ./start_server.sh
# 2. Start VSCode: F5 (launch extension)
# 3. Open Python file và test completions

# Evaluation
python tools/prompt_eval.py --server-url http://127.0.0.1:9000 \
  --api-key 5conmeo --input tools/tests.jsonl --out tools/results.csv
```

---

## 🎬 BẮT ĐẦU TỪ GIAI ĐOẠN NÀO?

**Tôi đề xuất bắt đầu từ GIAI ĐOẠN 1** vì nó fix các vấn đề cơ bản nhất và có impact ngay lập tức.

Sau khi tôi hoàn thành GIAI ĐOẠN 1, bạn sẽ test và chúng ta sẽ tiếp tục GIAI ĐOẠN 2.

---

## ❓ CÂU HỎI CHO BẠN

1. Bạn có muốn bắt đầu với **GIAI ĐOẠN 1** ngay không?
2. Bạn có muốn thay đổi thứ tự ưu tiên giai đoạn nào không?
3. Có tính năng nào đặc biệt bạn muốn ưu tiên hơn không?

**Hãy cho tôi biết để tôi bắt đầu implement! 🚀**
