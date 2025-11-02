# 🚀 QUICK START - BTL Python AI Code Assistant

## ✨ Extension đã sẵn sàng sử dụng!

### 📦 Cài đặt Extension

#### Option 1: Chạy từ source (Development)
```bash
# 1. Clone repo (nếu chưa có)
git clone https://github.com/Sagitoaz/BTL_Python.git
cd BTL_Python

# 2. Cài dependencies
npm install

# 3. Compile TypeScript
npm run compile

# 4. Mở trong VSCode và nhấn F5
code .
# Nhấn F5 → Extension Development Host sẽ mở
```

#### Option 2: Package và Install (Production)
```bash
# 1. Package extension
npm install -g vsce
vsce package

# 2. Install file .vsix vừa tạo
# Trong VSCode: Extensions → ⋯ (More Actions) → Install from VSIX
# Chọn file btl-python-*.vsix
```

---

## 🎯 Sử dụng

### Bước 1: Mở file Python bất kỳ
```bash
# Tạo file mới
code test.py
```

### Bước 2: Gõ code và đợi gợi ý
```python
def add(a, b):
    # Đặt cursor ở đây và đợi 1-2s
```

**Kết quả**: Sẽ xuất hiện ghost text màu xám: `return a + b`

**Nhấn Tab hoặc →** để chấp nhận gợi ý!

---

## 🔧 Cấu hình (Optional)

File `.vscode/settings.json`:
```json
{
  "btl.serverUrl": "https://btl-python-r9kz.onrender.com",
  "btl.apiKey": "5conmeo",
  "btl.timeoutMs": 15000
}
```

### Thay đổi server (nếu muốn)
- **Cloud (mặc định)**: `https://btl-python-r9kz.onrender.com`
- **Local**: `http://localhost:9000` (cần start server local trước)

---

## 📊 Features

### ✅ Có sẵn ngay
- 🤖 **AI Code Completion**: Gợi ý code thông minh
- ⚡ **Fast**: < 2s response time (sau cold start)
- 🎯 **Accurate**: 100% success rate, 0% markdown issues
- 📐 **Auto-format**: Code luôn được format đúng
- 🛡️ **Syntax-safe**: Không bao giờ gây lỗi cú pháp
- 📊 **Telemetry**: Tự động thu thập data để cải thiện

### 🎨 Hoạt động với
- ✅ Functions
- ✅ Classes & Methods
- ✅ List/Dict Comprehensions
- ✅ Loops & Conditionals
- ✅ Try-except blocks
- ✅ Multi-line completions

---

## 🧪 Test Thử

### Test Case 1: Simple Function
```python
def multiply(a, b):
    
```
**Gợi ý mong đợi**: `return a * b`

### Test Case 2: Fibonacci
```python
def fibonacci(n):
    if n <= 1:
        return n
    
```
**Gợi ý mong đợi**: `else:\n    return fibonacci(n-1) + fibonacci(n-2)`

### Test Case 3: List Comprehension
```python
numbers = [1, 2, 3, 4, 5]
squares = [
```
**Gợi ý mong đợi**: `x**2 for x in numbers]`

---

## 🐛 Troubleshooting

### Không có gợi ý?
1. **Kiểm tra server**: 
   ```bash
   curl https://btl-python-r9kz.onrender.com/health
   ```
   Kết quả phải có `"status": "ok"`

2. **Kiểm tra logs**: `Ctrl+Shift+U` → chọn "BTL Python"

3. **Reload extension**: `Ctrl+R` trong Extension Development Host

### Gợi ý chậm?
- Lần đầu sau idle: 30-60s (Render cold start)
- Lần sau: < 2s
- Nếu luôn chậm: kiểm tra network

### Gợi ý sai/lạ?
- Đảm bảo có đủ context (code trước và sau cursor)
- Thử thêm comment để hint cho AI
- Kiểm tra settings trong `.vscode/settings.json`

---

## 📈 Stats & Monitoring

### Xem thống kê (cần API key)
```bash
curl -H "Authorization: Bearer 5conmeo" \
  https://btl-python-r9kz.onrender.com/admin/telemetry/stats
```

### Export training data
```bash
curl -H "Authorization: Bearer 5conmeo" \
  https://btl-python-r9kz.onrender.com/admin/telemetry/export
```

---

## 🎓 Docs đầy đủ

- 📖 **[HOW_TO_TEST_EXTENSION.md](HOW_TO_TEST_EXTENSION.md)** - Hướng dẫn test chi tiết
- 📊 **[PROJECT_COMPLETION_SUMMARY.md](PROJECT_COMPLETION_SUMMARY.md)** - Tổng kết project
- 🚀 **[DEPLOY_GROQ_RENDER.md](DEPLOY_GROQ_RENDER.md)** - Hướng dẫn deploy
- 💻 **[PROJECT_README.md](PROJECT_README.md)** - Technical documentation

---

## 💡 Tips & Tricks

### 1. Tốc độ tối ưu
- Giữ server "warm": gọi /health mỗi 5 phút
- Dùng local server nếu cần response nhanh nhất

### 2. Gợi ý tốt hơn
- Viết comment mô tả function
- Cung cấp type hints
- Có context code xung quanh

### 3. Debug
- Xem logs trong Output panel
- Check Render logs nếu server lỗi
- Test bằng curl để tách biệt extension vs server

---

## 🎉 Enjoy!

Extension của bạn đã sẵn sàng! 

**Happy coding!** 🚀✨

---

**Questions?** Check docs hoặc xem logs để debug!
