# AI Code Completion Server

FastAPI server cung cấp code completion thông qua Ollama LLM.

## 🚀 Deploy nhanh lên Render

### Bước 1: Push code lên GitHub
```bash
git add .
git commit -m "Ready for Render deployment"
git push origin dev
```

### Bước 2: Deploy trên Render

1. Truy cập [render.com](https://dashboard.render.com)
2. New + → Web Service → Connect repo `Sagitoaz/BTL_Python`
3. Cấu hình:
   - **Root Directory**: `server`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. Set Environment Variables:
   - `OLLAMA_URL`: URL Ollama server của bạn
   - `MODEL`: `qwen2.5-coder:7b`
   - `API_KEY`: `5conmeo`

5. Click "Create Web Service"

### Bước 3: Test
```bash
# Thay YOUR_URL bằng URL Render của bạn
./scripts/test_render_server.sh https://your-app.onrender.com
```

## 📚 Tài liệu chi tiết

- [DEPLOY_RENDER.md](DEPLOY_RENDER.md) - Hướng dẫn đầy đủ
- [DEPLOY_CHECKLIST.md](../DEPLOY_CHECKLIST.md) - Checklist từng bước
- [.env.example](.env.example) - Ví dụ cấu hình

## ⚙️ Chạy local

```bash
# Cài dependencies
pip install -r requirements.txt

# Copy và điền .env
cp .env.example .env

# Start server
./start_server.sh
```

## 🔧 Environment Variables

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `OLLAMA_URL` | `http://127.0.0.1:11434` | URL Ollama server |
| `OLLAMA_API_KEY` | (trống) | API key cho Ollama Cloud |
| `MODEL` | `qwen2.5-coder:7b` | Model sử dụng |
| `API_KEY` | `5conmeo` | API key nội bộ |
| `PORT` | `9000` | Port server |
| `NUM_CTX` | `4096` | Context window |
| `POSTPROCESS_ENABLED` | `true` | Bật postprocessing |

## 🧪 Test

```bash
# Unit tests
pytest tests/

# Quick postprocessing test
python3 ../tools/test_postprocess_quick.py

# Batch evaluation
python3 ../tools/prompt_eval.py --server-url http://localhost:9000
```

## 📖 API Endpoints

### Health Check
```bash
GET /health
```

### Code Completion
```bash
POST /v1/completions
Content-Type: application/json
X-API-Key: 5conmeo

{
  "prefix": "def add(a, b):\n    ",
  "suffix": "\n",
  "language": "python",
  "max_tokens": 50,
  "temperature": 0.2
}
```

## 🐛 Troubleshooting

### 502 từ Ollama
- Check `OLLAMA_URL` đúng chưa
- Test: `curl $OLLAMA_URL/api/tags`
- Đảm bảo Ollama server đang chạy và accessible

### Kết quả vẫn có markdown
- Check `POSTPROCESS_ENABLED=true`
- Restart server sau khi đổi code

### Import errors
- Check `requirements.txt` đầy đủ
- Reinstall: `pip install -r requirements.txt`

## 📞 Support

Xem logs chi tiết trong Render Dashboard → Logs tab.
