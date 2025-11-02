# 🧪 HƯỚNG DẪN TEST EXTENSION TRONG VSCODE

## Bước 1: Mở Project trong VSCode

```bash
code /home/sagito/Desktop/BTL_Python
```

Hoặc: File → Open Folder → chọn `/home/sagito/Desktop/BTL_Python`

---

## Bước 2: Chạy Extension ở chế độ Debug

### Cách 1: Dùng phím tắt
1. Nhấn **F5** (hoặc Fn+F5 trên một số máy)
2. VSCode sẽ mở cửa sổ Extension Development Host mới

### Cách 2: Dùng menu
1. Vào menu **Run** → **Start Debugging**
2. Hoặc: View → Run → Click nút ▶️ màu xanh "Run Extension"

### Cách 3: Từ Command Palette
1. Nhấn **Ctrl+Shift+P** (hoặc Cmd+Shift+P trên Mac)
2. Gõ: **Debug: Start Debugging**
3. Enter

---

## Bước 3: Test Code Completion

Trong cửa sổ **Extension Development Host** mới (có dòng chữ "[Extension Development Host]" ở title bar):

### Test 1: Tạo file Python mới
1. **Ctrl+N** → tạo file mới
2. **Ctrl+K M** → chọn language: **Python**
3. Hoặc: File → New File → chọn Python

### Test 2: Gõ code và xem gợi ý

**Thử này:**
```python
def add(a, b):
    # Đặt con trỏ ở đây, sau 4 spaces, và đợi 1-2 giây
```

**Kết quả mong đợi:**
- Sau 1-2 giây, sẽ có gợi ý xuất hiện: `return a + b`
- Text màu xám (ghost text)
- Nhấn **Tab** hoặc **→** để accept

### Test 3: Thử các trường hợp khác

**Fibonacci:**
```python
def fibonacci(n):
    if n <= 1:
        return n
    # Đặt con trỏ ở đây
```

**Class method:**
```python
class Calculator:
    def multiply(self, a, b):
        # Đặt con trỏ ở đây
```

**List comprehension:**
```python
numbers = [1, 2, 3, 4, 5]
squares = [
    # Đặt con trỏ ở đây
```

---

## Bước 4: Xem Logs (nếu có lỗi)

### Output Panel
1. **Ctrl+Shift+U** → mở Output
2. Chọn dropdown: **BTL Python** hoặc **Extension Host**

### Debug Console
1. Trong cửa sổ VSCode chính (không phải Extension Development Host)
2. View → Debug Console
3. Xem logs real-time

---

## ⚙️ Cấu hình (nếu cần)

Kiểm tra `.vscode/settings.json`:

```json
{
  "btl.serverUrl": "https://btl-python-r9kz.onrender.com",
  "btl.apiKey": "5conmeo",
  "btl.timeoutMs": 15000
}
```

Nếu muốn đổi sang server local:
```json
{
  "btl.serverUrl": "http://localhost:9000",
  "btl.apiKey": "5conmeo"
}
```

---

## 🐛 Troubleshooting

### Không có gợi ý xuất hiện?

1. **Kiểm tra server:**
   ```bash
   curl https://btl-python-r9kz.onrender.com/health
   ```

2. **Xem Output logs:**
   - Ctrl+Shift+U
   - Chọn "BTL Python" trong dropdown
   - Xem có error gì không

3. **Reload extension:**
   - Trong Extension Development Host: Ctrl+R (reload)
   - Hoặc stop (Shift+F5) rồi F5 lại

### Gợi ý chậm?

- Lần đầu tiên sau idle: 30-60s (Render cold start)
- Lần sau: < 2s
- Nếu luôn chậm: kiểm tra network/timeout settings

### Gợi ý sai?

- Đảm bảo cursor ở đúng vị trí (cuối dòng hoặc đầu dòng mới)
- Prefix/suffix phải có context đủ
- Thử thêm comments để hint cho AI

---

## 📊 Test Checklist

- [ ] Extension compile thành công (`npm run compile`)
- [ ] F5 mở được Extension Development Host
- [ ] Tạo được file Python mới
- [ ] Gõ code → có ghost text xuất hiện
- [ ] Tab accept gợi ý
- [ ] Code được format đúng (no extra indent)
- [ ] Không có markdown fences (```)
- [ ] Thử 3-5 test cases khác nhau

---

## 🎯 Next Steps

Sau khi test OK:

1. **Package extension:**
   ```bash
   npm install -g vsce
   vsce package
   ```
   → Tạo file `.vsix`

2. **Install extension:**
   - Trong VSCode: Extensions → ⋯ → Install from VSIX
   - Chọn file `.vsix` vừa tạo

3. **Sử dụng hàng ngày:**
   - Extension sẽ tự động active khi mở file Python
   - Gợi ý sẽ xuất hiện tự động
   - Data sẽ được collect vào telemetry

---

## 🚀 Quick Start Commands

```bash
# 1. Compile
npm run compile

# 2. Mở VSCode
code /home/sagito/Desktop/BTL_Python

# 3. Nhấn F5 trong VSCode

# 4. Tạo file test.py trong Extension Development Host

# 5. Gõ code và test!
```

---

**Chúc bạn test thành công! 🎉**
