# ✅ SERVER ĐÃ DEPLOY THÀNH CÔNG!

## 🎉 Server URL
```
https://btl-python-r9kz.onrender.com
```

Server đã chạy nhưng status là **"degraded"** vì chưa kết nối được Ollama.

---

## 🔧 BƯỚC TIẾP THEO: Cấu hình Ollama

### Option 1: Dùng ngrok (KHUYÊN DÙNG - Nhanh nhất)

#### Bước 1: Chạy ngrok trên máy có Ollama

```bash
# Trên máy có Ollama (100.109.118.90 hoặc máy local)
cd ~/Desktop/BTL_Python
./scripts/expose_ollama_ngrok.sh
```

Hoặc chạy trực tiếp:
```bash
ngrok http 11434
```

Bạn sẽ thấy output như:
```
Forwarding    https://abc123-xyz.ngrok-free.app -> http://localhost:11434
```

#### Bước 2: Copy URL ngrok và set vào Render

1. Vào [Render Dashboard](https://dashboard.render.com/web/srv-xxx)
2. Tab **Environment**
3. Thêm/Edit biến:
   ```
   OLLAMA_URL=https://abc123-xyz.ngrok-free.app
   ```
4. Click **Save Changes**
5. Render sẽ tự động restart server (~30 giây)

#### Bước 3: Test lại

```bash
curl https://btl-python-r9kz.onrender.com/health
```

Kỳ vọng:
```json
{
  "status": "ok",
  "model": "qwen2.5-coder:7b",
  "available_models": ["qwen2.5-coder:7b"]
}
```

---

### Option 2: Dùng Cloudflare Tunnel (Miễn phí vĩnh viễn)

```bash
# Install cloudflared
# Linux:
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

# Chạy tunnel
cloudflared tunnel --url http://localhost:11434
```

Copy URL và set vào Render như ngrok.

---

### Option 3: Ollama Cloud (Nếu có tài khoản)

1. Đăng ký tại [ollama.com](https://ollama.com)
2. Lấy API key
3. Set trong Render:
   ```
   OLLAMA_URL=https://api.ollama.com
   OLLAMA_API_KEY=your-api-key-here
   ```

---

## 📝 CHECKLIST SAU KHI CÓ OLLAMA_URL

- [ ] Set `OLLAMA_URL` trong Render Environment
- [ ] Đợi Render restart (~30s)
- [ ] Test health: `curl https://btl-python-r9kz.onrender.com/health`
- [ ] Test completion (xem script bên dưới)
- [ ] Cập nhật extension với URL mới
- [ ] Test extension trong VSCode

---

## 🧪 TEST COMPLETION

```bash
curl -X POST https://btl-python-r9kz.onrender.com/complete \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 5conmeo" \
  -d '{
    "prefix": "def add(a, b):\n    ",
    "suffix": "\n",
    "language": "python",
    "max_tokens": 50,
    "temperature": 0.2
  }'
```

Kỳ vọng response:
```json
{
  "request_id": "abc123",
  "completion": "    return a + b"
}
```

✅ **Không có markdown** (```) nhờ postprocessing!

---

## 🔄 CẬP NHẬT EXTENSION

Sau khi server OK, cập nhật VSCode extension:

### File: `.vscode/settings.json`
```json
{
  "btl.serverUrl": "https://btl-python-r9kz.onrender.com",
  "btl.apiKey": "5conmeo"
}
```

Hoặc trong `src/extension.ts`:
```typescript
const serverUrl = cfg.get<string>("serverUrl") ?? 
                  "https://btl-python-r9kz.onrender.com";
```

### Compile và test
```bash
npm run compile
# Press F5 trong VSCode để test extension
```

---

## 📊 MONITORING

### Xem logs real-time
1. Vào [Render Dashboard](https://dashboard.render.com)
2. Chọn service `btl-python-server`
3. Tab **Logs**

### Check metrics
- Tab **Metrics**: CPU, Memory, Request count
- Tab **Events**: Deploy history

---

## ⚠️ LƯU Ý QUAN TRỌNG

### 1. Về ngrok
- ⏰ URL sẽ đổi mỗi khi restart ngrok
- 🔄 Mỗi lần restart phải update lại `OLLAMA_URL` trong Render
- 💰 Ngrok free: giới hạn 1 tunnel, session timeout 2h (reconnect tự động)

### 2. Về Render Free Tier
- 💤 Server sleep sau 15 phút không dùng
- ⏱️ Cold start: ~30 giây lần đầu
- 🔄 Mỗi deploy mới sẽ mất ~2-3 phút

### 3. Performance
- 📡 Latency: Client → Render → ngrok/Ollama → back
- ⚡ Có thể chậm hơn khi dùng local
- 🚀 Upgrade Render Starter ($7/tháng) để không sleep

---

## 🐛 TROUBLESHOOTING

### Server vẫn "degraded"
```bash
# Check OLLAMA_URL có đúng không
curl $OLLAMA_URL/api/tags

# Nếu fail, ngrok/tunnel chưa chạy hoặc URL sai
```

### 502 Bad Gateway
- Ollama server không chạy
- ngrok/tunnel đã đóng
- Firewall chặn

### Extension không connect
- Check server URL trong settings
- Check API key đúng chưa
- Test trước bằng curl

---

## 🎯 TIẾP THEO

Sau khi có OLLAMA_URL và server chạy OK:

1. ✅ Test postprocessing
2. ✅ Test với extension
3. ✅ Monitor performance
4. 🚀 **Tiếp tục GIAI ĐOẠN 2**: Code Formatter Integration

---

## 📞 BÁO CÁO KẾT QUẢ

Sau khi set OLLAMA_URL, hãy test và báo tôi:

```
✅ Health endpoint: [OK/FAIL]
✅ Completion test: [OK/FAIL]  
✅ No markdown in output: [YES/NO]
✅ Extension connects: [OK/FAIL]

Issues (nếu có):
- [Mô tả vấn đề]
```

**Bạn đang ở bước nào? Tôi sẽ hỗ trợ tiếp! 🚀**
