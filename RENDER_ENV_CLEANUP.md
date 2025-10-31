## 🔥 RENDER ENVIRONMENT CLEANUP

Lỗi deploy vì Render vẫn còn env vars cũ của Ollama!

### Fix ngay:

1. Vào Render dashboard: https://dashboard.render.com/web/btl-python-r9kz
2. Click tab **Environment**
3. **XÓA** các biến này:
   - ❌ `OLLAMA_URL`
   - ❌ `MODEL`
   - ❌ `OLLAMA_API_KEY` (nếu có)

4. **THÊM** biến mới (nếu chưa có):
   - ✅ `GROQ_API_KEY` = `gsk_...` (lấy từ console.groq.com)
   - ✅ `GROQ_MODEL` = `llama-3.1-70b-versatile`

5. **Click "Save Changes"** → Render sẽ tự động redeploy

### Hoặc dùng lệnh:

```bash
# Nếu có Render CLI
render env:set GROQ_API_KEY=gsk_your_key_here
render env:set GROQ_MODEL=llama-3.1-70b-versatile
render env:delete OLLAMA_URL
render env:delete MODEL
render env:delete OLLAMA_API_KEY
```

### Note:
Tôi đã fix code thêm `extra = "ignore"` trong config.py để tạm thời bỏ qua các env vars cũ, nhưng tốt nhất là xóa chúng đi.
