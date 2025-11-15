# Giải thích chi tiết: `server/app/core/config.py`

## 📋 Mục đích của file

File này quản lý **tất cả cấu hình** của backend server. Thay vì hardcode các giá trị như API key, port, timeout vào code, ta tập trung chúng vào 1 file để dễ quản lý và bảo mật.

## 🔍 Phân tích từng dòng code

### Import statements

```python
from pydantic_settings import BaseSettings
```

**Giải thích:**
- `pydantic_settings` là thư viện giúp quản lý settings theo kiểu type-safe
- `BaseSettings`: Class cha để tạo settings với khả năng:
  - Đọc từ file `.env` tự động
  - Validate kiểu dữ liệu (str, int, bool)
  - Có giá trị mặc định

**Ví dụ tương tự:** Giống như form nhập liệu có validation, nếu bạn nhập PORT="abc" (string) thay vì số, Pydantic sẽ báo lỗi ngay.

---

### Class Settings

```python
class Settings(BaseSettings):
```

**Giải thích:**
- Kế thừa từ `BaseSettings` để có các tính năng tự động
- Class này chứa tất cả biến cấu hình của hệ thống

---

### Groq API Configuration

```python
    # Groq Cloud API - Get your key from console.groq.com
    GROQ_API_KEY: str = ""
```

**Giải thích:**
- `GROQ_API_KEY: str` → Biến kiểu string, bắt buộc có để gọi Groq API
- `= ""` → Giá trị mặc định rỗng (nếu không set trong .env)
- Comment hướng dẫn user lấy key ở đâu

**Flow thực tế:**
1. User tạo account ở https://console.groq.com
2. Tạo API key mới
3. Copy key vào file `.env`:
   ```
   GROQ_API_KEY=gsk_abc123xyz...
   ```
4. Pydantic tự động đọc từ .env vào biến này

---

```python
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
```

**Giải thích:**
- Tên model LLM sẽ sử dụng
- Mặc định: `llama-3.3-70b-versatile` (model mới nhất, chất lượng cao)
- Có thể đổi thành:
  - `llama-3.1-8b-instant` → Nhanh hơn, nhẹ hơn
  - `mixtral-8x7b-32768` → Context dài hơn

**Comment trong code:**
```python
    # Recommended models (updated Nov 2025):
    # - llama-3.3-70b-versatile (newest, best quality)
    # - llama-3.1-8b-instant (fastest)
    # - mixtral-8x7b-32768 (large context)
```
→ Liệt kê options để developer dễ chọn

---

### Server Configuration

```python
    HOST: str = "0.0.0.0"
    PORT: int = 9000
```

**Giải thích HOST:**
- `0.0.0.0` → Listen trên TẤT CẢ network interfaces
- Nghĩa là server chấp nhận kết nối từ:
  - `localhost` (127.0.0.1)
  - Local network (192.168.x.x)
  - Internet (public IP)

**So sánh:**
- `127.0.0.1` → Chỉ chấp nhận từ localhost (dev mode)
- `0.0.0.0` → Chấp nhận từ mọi nơi (production mode)

**Giải thích PORT:**
- `9000` → Server chạy trên cổng 9000
- Có thể truy cập: `http://localhost:9000`

**Override bằng environment variable:**
```bash
PORT=8080 python -m uvicorn app.main:app
# Sẽ dùng port 8080 thay vì 9000
```

---

### API Key Protection

```python
    # Internal server API key (for protecting this FastAPI server)
    API_KEY: str = "5conmeo"
```

**Giải thích:**
- API key để bảo vệ backend khỏi truy cập trái phép
- Client (VS Code extension) phải gửi key này trong header:
  ```
  Authorization: Bearer 5conmeo
  ```
- **MẶC ĐỊNH:** `"5conmeo"` (demo key, nên đổi trong production)

**Flow bảo mật:**
```
Client Request → Backend check API_KEY → 
  ✅ Match → Xử lý request
  ❌ Not match → 403 Forbidden
```

**Best practice:**
```bash
# .env file (không commit lên Git)
API_KEY=super_secret_key_production_2024
```

---

### LLM Request Tuning

```python
    NUM_CTX: int = 4096
    TIMEOUT_SECONDS: int = 120
```

**NUM_CTX (Context Size):**
- Số tokens tối đa cho context window
- `4096` tokens ≈ 3000 từ tiếng Anh
- LLM có thể "nhìn thấy" tối đa 4096 tokens (prefix + suffix + prompt)

**Ví dụ:**
```python
prefix = "def fibonacci(n):\n    " # ~10 tokens
suffix = ""                          # 0 tokens
prompt template = "..."              # ~500 tokens
few-shot examples = "..."            # ~1000 tokens
───────────────────────────────────
Total: ~1510 tokens < 4096 ✅ OK
```

**TIMEOUT_SECONDS:**
- Thời gian chờ tối đa cho 1 request LLM
- `120` giây = 2 phút
- Nếu Groq không response sau 2 phút → Cancel request, trả lỗi

**Tại sao cần timeout?**
- Tránh request bị "treo" mãi mãi
- Nếu Groq API down/chậm, user sẽ nhận lỗi thay vì chờ vô hạn

---

### CORS and Middleware

```python
    ALLOW_ORIGINS: str = "*"
```

**CORS (Cross-Origin Resource Sharing):**
- Cho phép request từ domain nào?
- `"*"` → Cho phép TẤT CẢ origins (mọi website đều gọi được API)

**Ví dụ:**
```
VS Code extension (chạy local) → Backend (Render.com)
Origin: vscode-local → Backend check ALLOW_ORIGINS="*" → ✅ Allow
```

**Security note:**
- Production nên giới hạn: `"https://myapp.com, https://vscode.dev"`
- Nhưng vì đây là tool internal → `*` OK

---

```python
    HEADERS_MIDDLEWARE: str = "X-Request-ID"
    REQUEST_ID: str = "request_id"
```

**X-Request-ID Header:**
- Mỗi request sẽ có unique ID (UUID)
- Dùng để track request qua nhiều layers (logs, debugging)

**Flow:**
```
1. Request vào → Middleware gắn X-Request-ID: abc-123
2. Log: [abc-123] Processing completion
3. Log: [abc-123] Calling Groq API
4. Log: [abc-123] Response sent
→ Tất cả logs của 1 request có cùng ID, dễ trace
```

---

```python
    POSTPROCESS_ENABLED: bool = True
```

**Postprocessing:**
- Sau khi LLM trả về text, có xử lý thêm không?
- `True` → Bật các bước:
  - Strip markdown fences (```python)
  - Remove duplicate code
  - Cut at stop sequences
  - Align indentation

**Ví dụ:**
```python
# LLM raw output:
```python
return a + b
```

# Sau postprocess:
return a + b
```

---

```python
    AUTO_FORMAT: bool = True  # Auto-format completions with black/autopep8
```

**Auto-formatting:**
- `True` → Tự động format code bằng `black` (Python) hoặc `clang-format` (C++)
- `False` → Giữ nguyên output của LLM

**Ví dụ:**
```python
# LLM output (không chuẩn PEP 8):
def foo( x,y ):
  return x+y

# Sau black format:
def foo(x, y):
    return x + y
```

**Fallback chain:**
```
black → (fail) → autopep8 → (fail) → raw output
```

---

### Config Inner Class

```python
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
```

**Giải thích từng dòng:**

**`env_file = ".env"`**
- Pydantic tự động đọc file `.env` trong thư mục server/
- File `.env` chứa secrets không commit lên Git

**`case_sensitive = False`**
- Không phân biệt hoa thường cho tên biến
- `GROQ_API_KEY`, `groq_api_key`, `Groq_Api_Key` → Đều map vào cùng 1 biến

**`extra = "ignore"`**
- Nếu `.env` có biến không có trong class Settings → Bỏ qua (không báo lỗi)
- Ví dụ: File có `OLD_UNUSED_VAR=123` → Pydantic không complain

**Tại sao cần ignore?**
- Khi migrate code (vd: đổi từ Ollama → Groq), các biến cũ như `OLLAMA_URL` vẫn nằm trong `.env`
- Với `extra="ignore"` → Code vẫn chạy, không crash

---

### Singleton Instance

```python
settings = Settings()
```

**Giải thích:**
- Tạo 1 instance duy nhất của Settings
- Các file khác import và dùng chung instance này:
  ```python
  from app.core.config import settings
  
  print(settings.GROQ_API_KEY)  # Truy cập giá trị
  ```

**Pattern: Singleton**
- Chỉ có 1 object Settings trong toàn bộ app
- Tránh đọc file `.env` nhiều lần (performance)

---

## 🎯 Tổng kết flow hoạt động

### 1. Khi server khởi động:

```python
# main.py
from app.core.config import settings  # ← Dòng này trigger

# Flow:
1. Pydantic tìm file .env
2. Đọc các biến: GROQ_API_KEY=gsk_xxx, PORT=9000, ...
3. Parse và validate kiểu dữ liệu
4. Gắn vào settings object
5. settings.GROQ_API_KEY → "gsk_xxx"
```

### 2. Trong request handler:

```python
# completions.py
from app.core.config import settings

async def complete(req):
    if settings.POSTPROCESS_ENABLED:  # ← Dùng config
        # Xử lý postprocess
    
    if settings.AUTO_FORMAT:  # ← Dùng config
        # Format code
```

### 3. Khi call Groq API:

```python
# groq.py
headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
response = httpx.post(
    "https://api.groq.com/...",
    headers=headers,
    json={"model": settings.GROQ_MODEL, ...}
)
```

---

## 🔧 Cách sử dụng trong thực tế

### Development (.env local):

```bash
# server/.env
GROQ_API_KEY=gsk_dev_test_key_123
GROQ_MODEL=llama-3.1-8b-instant  # Model nhỏ để test nhanh
API_KEY=dev_secret
PORT=9000
AUTO_FORMAT=false  # Tắt format để debug dễ hơn
```

### Production (Render.com Environment Variables):

```
GROQ_API_KEY=gsk_prod_real_key_xyz
GROQ_MODEL=llama-3.3-70b-versatile  # Model tốt nhất
API_KEY=super_secure_production_key
PORT=$PORT  # Render tự động set
AUTO_FORMAT=true  # Bật format cho output đẹp
```

---

## 💡 Những điểm quan trọng khi thuyết trình

1. **Tại sao dùng Pydantic thay vì dict thường?**
   - Type safety: Catch lỗi lúc startup thay vì runtime
   - Auto validation: PORT phải là int, không thể là "abc"
   - Auto completion: IDE suggest các config có sẵn

2. **Tại sao tách config ra file riêng?**
   - Single source of truth
   - Dễ đổi cấu hình mà không sửa code logic
   - Bảo mật: `.env` không commit lên Git

3. **Tại sao cần API_KEY cho backend?**
   - Tránh spam/abuse từ bên ngoài
   - Rate limiting theo API key
   - Track usage của từng client

4. **Các biến quan trọng nhất:**
   - `GROQ_API_KEY`: Không có = không gọi được LLM
   - `API_KEY`: Bảo vệ backend
   - `GROQ_MODEL`: Quyết định chất lượng completion
   - `AUTO_FORMAT`: Ảnh hưởng output cuối cùng

---

## 📊 Diagram: Config Flow

```
┌─────────────────────────────────────────────────────┐
│                    .env file                         │
│  GROQ_API_KEY=gsk_xxx                               │
│  PORT=9000                                          │
│  API_KEY=5conmeo                                    │
└─────────────────┬───────────────────────────────────┘
                  │
                  │ Pydantic reads at startup
                  ↓
┌─────────────────────────────────────────────────────┐
│            Settings Object (Singleton)               │
│  settings.GROQ_API_KEY = "gsk_xxx"                  │
│  settings.PORT = 9000                               │
│  settings.API_KEY = "5conmeo"                       │
└─────────────────┬───────────────────────────────────┘
                  │
                  │ Import in multiple files
                  ↓
      ┌───────────┼───────────┬──────────────┐
      │           │           │              │
      ↓           ↓           ↓              ↓
  main.py    groq.py   completions.py   security.py
  (CORS)    (API key)   (postprocess)   (validate)
```

---

**File này hoàn tất!** Tiếp theo tôi sẽ giải thích `http.py`. Bạn muốn tôi tiếp tục không?
