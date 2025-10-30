# ✅ Checklist Deploy Server lên Render

## 📋 Trước khi deploy

- [ ] Code đã được test kỹ trên local
- [ ] File `server/requirements.txt` có đầy đủ dependencies
- [ ] Đã có Ollama endpoint có thể truy cập từ internet (hoặc dùng ngrok)
- [ ] Đã push code lên GitHub

## 🔐 Chuẩn bị thông tin

- [ ] **OLLAMA_URL**: URL của Ollama server
  - Nếu dùng local + ngrok: chạy `scripts/expose_ollama_ngrok.sh` và copy URL
  - Nếu có Ollama Cloud: lấy URL từ dashboard
  - Nếu có server riêng: đảm bảo có public IP và port mở

- [ ] **OLLAMA_API_KEY** (nếu cần): API key cho Ollama Cloud

## 🚀 Deploy trên Render

### Bước 1: Tạo Web Service
- [ ] Đăng nhập [render.com](https://dashboard.render.com)
- [ ] Click "New +" → "Web Service"
- [ ] Connect GitHub repo `Sagitoaz/BTL_Python`
- [ ] Chọn branch `dev`

### Bước 2: Cấu hình Service
- [ ] **Name**: `btl-python-server`
- [ ] **Region**: `Singapore`
- [ ] **Root Directory**: `server`
- [ ] **Runtime**: `Python 3`
- [ ] **Build Command**: `pip install -r requirements.txt`
- [ ] **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- [ ] **Instance Type**: `Free` (hoặc Starter $7/tháng)

### Bước 3: Set Environment Variables
Click vào tab "Environment" và thêm:

- [ ] `OLLAMA_URL` = `<your-ollama-url>`
- [ ] `OLLAMA_API_KEY` = `<your-key>` (nếu cần)
- [ ] `MODEL` = `qwen2.5-coder:7b`
- [ ] `API_KEY` = `5conmeo`
- [ ] `NUM_CTX` = `4096`
- [ ] `POSTPROCESS_ENABLED` = `true`

### Bước 4: Deploy
- [ ] Click "Create Web Service"
- [ ] Đợi 2-5 phút để deploy

## ✅ Sau khi deploy

### Test server
- [ ] Lấy URL từ Render (vd: `https://btl-python-server.onrender.com`)
- [ ] Test health endpoint:
```bash
curl https://btl-python-server.onrender.com/health
```
Expected:
```json
{"status":"ok","model":"qwen2.5-coder:7b"}
```

- [ ] Test completion endpoint:
```bash
curl -X POST https://btl-python-server.onrender.com/v1/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 5conmeo" \
  -d '{
    "prefix": "def add(a, b):\n    ",
    "suffix": "\n\nprint(add(1, 2))",
    "language": "python",
    "max_tokens": 50
  }'
```

### Cập nhật VSCode Extension
- [ ] Mở `src/extension.ts` hoặc `src/inlineProvider.ts`
- [ ] Đổi server URL thành URL Render của bạn:
```typescript
const SERVER_URL = "https://btl-python-server.onrender.com";
```
- [ ] Build lại extension: `npm run compile`
- [ ] Test extension trong VSCode

### Monitor
- [ ] Xem logs trong Render Dashboard → Logs
- [ ] Kiểm tra usage trong Render Dashboard → Metrics

## 🐛 Nếu có lỗi

### Server không start được
- [ ] Xem logs trong Render Dashboard
- [ ] Kiểm tra `requirements.txt` có đầy đủ không
- [ ] Kiểm tra syntax errors trong code

### 502 Bad Gateway từ Ollama
- [ ] Test OLLAMA_URL từ terminal: `curl $OLLAMA_URL/api/tags`
- [ ] Kiểm tra Ollama server có đang chạy không
- [ ] Kiểm tra firewall/network có chặn không

### Extension không kết nối được server
- [ ] Kiểm tra CORS settings (`ALLOW_ORIGINS=*`)
- [ ] Kiểm tra API_KEY đúng chưa
- [ ] Test từ browser trước: mở `https://your-server.onrender.com/health`

### Server bị sleep (Free tier)
- [ ] Upgrade lên Starter plan ($7/tháng)
- [ ] Hoặc setup cron job ping server mỗi 10 phút

## 📚 Tài liệu tham khảo
- [DEPLOY_RENDER.md](DEPLOY_RENDER.md) - Hướng dẫn chi tiết
- [Render Python Docs](https://render.com/docs/deploy-fastapi)
- [Ollama API Docs](https://github.com/ollama/ollama/blob/main/docs/api.md)
