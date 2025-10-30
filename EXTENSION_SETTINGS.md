# Hướng dẫn cấu hình Extension Development (Ubuntu)

## Sau khi nhấn F5, cửa sổ Extension Development Host mở ra:

### Cách 1: Cấu hình qua UI
1. Nhấn `Ctrl + ,` để mở Settings
2. Tìm "btl" trong thanh search
3. Điền các giá trị:
   - **BTL: Server Url**: `http://100.109.118.90:9000`
   - **BTL: Api Key**: `5conmeo`
   - **BTL: Python Path**: `/home/sagito/venv/bin/python`
   - **BTL: Enable Streaming**: `false`
   - **BTL: Timeout Ms**: `8000`

### Cách 2: Copy JSON settings (Nhanh hơn)
1. Trong cửa sổ Extension Development Host, nhấn `Ctrl + Shift + P`
2. Gõ: `Preferences: Open User Settings (JSON)`
3. Copy và paste đoạn này vào:

```json
{
  "btl.serverUrl": "http://100.109.118.90:9000",
  "btl.apiKey": "5conmeo",
  "btl.pythonPath": "/home/sagito/venv/bin/python",
  "btl.enableStreaming": false,
  "btl.timeoutMs": 8000
}
```

4. Save file (Ctrl + S)
5. Tạo file Python mới để test, ví dụ: `test.py`
6. Gõ code và xem gợi ý xuất hiện!

## Test xem extension hoạt động:
1. Tạo file `test.py` trong Extension Development Host
2. Gõ:
```python
def add(a, b):
    
```
3. Extension sẽ gợi ý code completion! ✨

## Nếu có lỗi trong Debug Console:
- Kiểm tra Tailscale đã bật chưa
- Test server: `curl http://100.109.118.90:9000/health -H "X-API-Key: 5conmeo"`
- Xem log ở tab "Debug Console" trong VS Code chính
