# Deploy Server lên Render.com

## 📋 Yêu cầu

1. **Tài khoản GitHub** - Push code lên GitHub repo
2. **Tài khoản Render** - Đăng ký miễn phí tại [render.com](https://render.com)
3. **Ollama endpoint** - Cần 1 server Ollama đang chạy và có thể truy cập từ internet

## 🚀 Các bước deploy

### Bước 1: Chuẩn bị code

Code đã sẵn sàng! Các file cần thiết:
- ✅ `Procfile` - Render sẽ dùng để khởi động server
- ✅ `server/app/core/config.py` - Đọc env variables
- ✅ `server/requirements.txt` hoặc `server/requirements-dev.txt` - Dependencies

### Bước 2: Push code lên GitHub

```bash
cd ~/Desktop/BTL_Python
git add .
git commit -m "Chuẩn bị deploy lên Render"
git push origin dev
```

### Bước 3: Tạo Web Service trên Render

1. Đăng nhập vào [dashboard.render.com](https://dashboard.render.com)
2. Click **"New +"** → chọn **"Web Service"**
3. Chọn **"Build and deploy from a Git repository"**
4. Connect GitHub repo `Sagitoaz/BTL_Python`
5. Cấu hình như sau:

#### ⚙️ Cấu hình cơ bản

| Trường | Giá trị |
|--------|---------|
| **Name** | `btl-python-server` (hoặc tên bạn muốn) |
| **Region** | Singapore (gần VN nhất) |
| **Branch** | `dev` |
| **Root Directory** | `server` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | `Free` (hoặc trả phí nếu cần) |

### Bước 4: Cấu hình Environment Variables

Trong phần **Environment** của Web Service, thêm các biến sau:

#### 🔐 Biến bắt buộc

```
OLLAMA_URL=https://your-ollama-endpoint.com
```
Hoặc nếu bạn có Ollama chạy trên server khác:
```
OLLAMA_URL=http://100.109.118.90:11434
```
⚠️ **LƯU Ý**: Nếu dùng IP nội bộ Tailscale, Render sẽ KHÔNG kết nối được!

#### 🔑 Biến tùy chọn

```
OLLAMA_API_KEY=your-ollama-api-key-if-needed
API_KEY=5conmeo
MODEL=qwen2.5-coder:7b
NUM_CTX=4096
POSTPROCESS_ENABLED=true
```

### Bước 5: Deploy

1. Click **"Create Web Service"**
2. Render sẽ tự động:
   - Clone repo
   - Cài dependencies
   - Chạy server
3. Đợi 2-5 phút để deploy xong

### Bước 6: Lấy URL và test

Sau khi deploy xong, Render sẽ cho bạn URL dạng:
```
https://btl-python-server.onrender.com
```

Test ngay:
```bash
curl https://btl-python-server.onrender.com/health
```

Kết quả mong đợi:
```json
{
  "status": "ok",
  "model": "qwen2.5-coder:7b",
  "available_models": ["qwen2.5-coder:7b"]
}
```

## 🔧 Cấu hình VSCode Extension

Sau khi có URL Render, cập nhật trong extension:

1. Mở `src/extension.ts` hoặc setting
2. Đổi server URL:
```typescript
const serverUrl = "https://btl-python-server.onrender.com";
```

## 📌 Giải pháp cho vấn đề Ollama endpoint

### Vấn đề: Render không kết nối được Ollama nội bộ

Nếu Ollama của bạn chạy trên mạng nội bộ (Tailscale, localhost), Render sẽ KHÔNG thể kết nối.

### Giải pháp 1: Dùng Ollama Cloud (KHUYÊN DÙNG)

1. Đăng ký tại [ollama.com/cloud](https://ollama.com) (nếu có)
2. Lấy API key
3. Set env vars:
```
OLLAMA_URL=https://api.ollama.com
OLLAMA_API_KEY=your-api-key
```

### Giải pháp 2: Expose Ollama ra internet

Dùng **ngrok** hoặc **Cloudflare Tunnel**:

#### Với ngrok:
```bash
# Trên máy chạy Ollama
ngrok http 11434
```

Lấy URL ngrok (vd: `https://abc123.ngrok.io`) và set:
```
OLLAMA_URL=https://abc123.ngrok.io
```

#### Với Cloudflare Tunnel:
```bash
cloudflared tunnel --url http://localhost:11434
```

### Giải pháp 3: Deploy Ollama lên cloud khác

Deploy Ollama lên:
- AWS EC2 với GPU
- Google Cloud Platform
- Paperspace
- RunPod

## 🐛 Troubleshooting

### Lỗi 502 Bad Gateway từ Ollama
- Kiểm tra `OLLAMA_URL` có đúng không
- Kiểm tra Ollama server có đang chạy không
- Test kết nối: `curl $OLLAMA_URL/api/tags`

### Server bị sleep (Free tier)
Render free tier sẽ sleep sau 15 phút không dùng. Giải pháp:
- Upgrade lên paid tier ($7/tháng)
- Hoặc dùng cron job để ping server mỗi 10 phút

### Logs bị lỗi
Xem logs trong Render Dashboard → Web Service → Logs

### Import errors
Đảm bảo `requirements.txt` có đầy đủ:
```txt
fastapi
uvicorn[standard]
pydantic-settings
requests
```

## 💰 Chi phí

- **Free tier**: $0/tháng
  - 750 giờ/tháng
  - Sleep sau 15 phút không dùng
  - 512MB RAM
  
- **Starter**: $7/tháng
  - Không sleep
  - 512MB RAM

## 📚 Tài liệu thêm

- [Render Python Docs](https://render.com/docs/deploy-fastapi)
- [Render Environment Variables](https://render.com/docs/environment-variables)
