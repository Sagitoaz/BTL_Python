# Giải thích chi tiết: `server/app/core/http.py`

## 📋 Mục đích của file

File này tạo ra **HTTP client có khả năng retry tự động** để gọi API bên ngoài (Groq). Thay vì dùng `requests.get()` trực tiếp (không có retry), ta wrap nó với retry logic để tăng độ tin cậy.

## 🔍 Phân tích từng dòng code

### Import statements

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import settings
```

**Giải thích từng import:**

**`import requests`**
- Thư viện HTTP client phổ biến nhất trong Python
- Dùng để gửi GET, POST, PUT, DELETE requests

**`from requests.adapters import HTTPAdapter`**
- Adapter: Lớp xử lý low-level HTTP transport
- Cho phép customize behavior (retry, timeout, connection pooling)

**`from urllib3.util.retry import Retry`**
- Class cấu hình retry logic
- urllib3: HTTP library mà requests dùng bên dưới

**`from app.core.config import settings`**
- Import settings để lấy TIMEOUT_SECONDS

---

## 🔧 Function: `make_session()`

```python
def make_session() -> requests.Session:
```

**Giải thích:**
- Tạo một `Session` object với retry logic đã config
- `-> requests.Session`: Type hint → Return về Session object

**Tại sao dùng Session thay vì requests.get() trực tiếp?**
- Session **tái sử dụng** TCP connection (connection pooling)
- Nhanh hơn khi gọi nhiều requests liên tiếp
- Có thể customize headers, cookies, retry một lần cho tất cả requests

**Ví dụ so sánh:**

```python
# Không dùng Session (chậm):
for i in range(10):
    requests.get("https://api.groq.com/...")
# → Mở 10 TCP connections mới

# Dùng Session (nhanh):
session = requests.Session()
for i in range(10):
    session.get("https://api.groq.com/...")
# → Tái sử dụng 1 connection
```

---

### Create Session Object

```python
    s = requests.Session()
```

**Giải thích:**
- Tạo Session object rỗng
- Chưa có retry logic, phải thêm vào

---

### Configure Retry Strategy

```python
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
    )
```

**Phân tích từng parameter:**

#### `total=3`

**Ý nghĩa:**
- Số lần retry tối đa = 3
- Request ban đầu + 3 retries = tối đa 4 attempts

**Flow:**
```
Request #1 → Fail (502 Bad Gateway)
  ↓ Retry 1
Request #2 → Fail (503 Service Unavailable)
  ↓ Retry 2
Request #3 → Fail (504 Gateway Timeout)
  ↓ Retry 3
Request #4 → Success (200 OK) ✅
```

---

#### `backoff_factor=0.5`

**Ý nghĩa:**
- Thời gian chờ giữa các retry theo công thức:
  ```
  wait_time = backoff_factor * (2 ^ retry_number)
  ```

**Tính toán cụ thể:**
```
Retry 1: 0.5 * (2^0) = 0.5 * 1  = 0.5 giây
Retry 2: 0.5 * (2^1) = 0.5 * 2  = 1.0 giây
Retry 3: 0.5 * (2^2) = 0.5 * 4  = 2.0 giây
```

**Timeline:**
```
Request #1 (fail) 
  → Wait 0.5s → Request #2 (fail)
  → Wait 1.0s → Request #3 (fail)
  → Wait 2.0s → Request #4 (success)

Total time = 0.5 + 1.0 + 2.0 = 3.5 giây (trước khi success)
```

**Tại sao dùng exponential backoff?**
- Nếu API đang overload, retry ngay lập tức sẽ làm tình hình tồi tệ hơn
- Chờ càng lâu càng cho API thời gian recover

---

#### `status_forcelist=(429, 502, 503, 504)`

**Ý nghĩa:**
- Chỉ retry khi response code là một trong các code này
- Không retry với 4xx client errors (400, 401, 403, 404)

**Phân tích từng status code:**

**429 - Too Many Requests**
- API rate limit exceeded
- Retry có ý nghĩa vì sau 1-2 giây rate limit reset

**502 - Bad Gateway**
- Server trung gian (gateway/proxy) không kết nối được tới upstream server
- Temporary issue, retry có thể thành công

**503 - Service Unavailable**
- Server tạm thời quá tải hoặc đang maintenance
- Retry sau vài giây có thể OK

**504 - Gateway Timeout**
- Gateway không nhận được response từ upstream server đúng hạn
- Có thể do network issue, retry có ý nghĩa

**Tại sao KHÔNG retry 4xx errors?**

```python
# 400 Bad Request → Lỗi do request sai, retry cũng fail
# 401 Unauthorized → API key sai, retry vô ích
# 403 Forbidden → Không có quyền, retry không giải quyết
# 404 Not Found → Endpoint không tồn tại, retry vô nghĩa
```

---

#### `allowed_methods=frozenset({"GET", "POST"})`

**Ý nghĩa:**
- Chỉ retry cho GET và POST requests
- Không retry PUT, DELETE, PATCH

**Tại sao?**

**GET: Safe to retry**
- Idempotent (gọi nhiều lần = gọi 1 lần)
- Không thay đổi state của server
- VD: `GET /api/user/123` → Retry OK

**POST: Depends (nhưng trong trường hợp này OK)**
- Không idempotent trong general case
- Nhưng với Groq completion API, POST là stateless:
  ```python
  # Gọi 1 lần:
  POST /complete {"prefix": "def add("}
  → Response: "a, b): return a + b"
  
  # Gọi lại (retry):
  POST /complete {"prefix": "def add("}
  → Response: "a, b): return a + b" (same result)
  ```
- Không tạo resource mới, chỉ compute và trả về

**PUT/DELETE: NOT safe to retry**
- PUT: Update resource → Retry có thể ghi đè không mong muốn
- DELETE: Xóa resource → Retry sau khi đã xóa = error

**frozenset vs set:**
- `frozenset`: Immutable set (không thể thay đổi)
- Performance: Nhanh hơn set thường một chút
- Signal intent: "Danh sách này không bao giờ thay đổi"

---

### Mount Adapters to Session

```python
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
```

**Giải thích:**

**`s.mount(prefix, adapter)`**
- "Mount" một adapter vào Session cho URLs matching prefix
- Mọi request tới URLs bắt đầu bằng prefix sẽ dùng adapter này

**`HTTPAdapter(max_retries=retry)`**
- Tạo adapter với retry strategy đã config ở trên
- `max_retries=retry`: Truyền Retry object vào adapter

**Tại sao phải mount 2 lần (http:// và https://)?**
- Session routes requests based on URL scheme
- `http://` URLs → Adapter 1
- `https://` URLs → Adapter 2
- Trong thực tế chỉ dùng `https://` (Groq API), nhưng mount cả 2 để đảm bảo

**Flow khi gọi API:**
```python
session.post("https://api.groq.com/...")
  ↓
Session check: URL starts with "https://"
  ↓
Use HTTPAdapter mounted for "https://"
  ↓
Adapter apply retry logic
  ↓
Make actual HTTP request
```

---

### Return Session

```python
    return s
```

**Giải thích:**
- Trả về Session đã config
- Caller có thể dùng ngay: `session.post(...)`

---

## 🌍 Global Session Instance

```python
SESSION = make_session()
```

**Giải thích:**
- Tạo 1 session duy nhất khi import module
- Pattern: Module-level singleton
- Tất cả các module khác dùng chung SESSION này

**Tại sao dùng singleton?**
- Connection pooling: Tái sử dụng connections
- Performance: Không tạo session mới mỗi request
- Memory: 1 session thay vì 100 sessions

**Usage trong code khác:**
```python
# groq.py
from app.core.http import SESSION

response = SESSION.post(
    "https://api.groq.com/...",
    json={...}
)
```

---

## ⏱️ Global Timeout

```python
TIMEOUT = settings.TIMEOUT_SECONDS
```

**Giải thích:**
- Lấy timeout từ config (mặc định 120 giây)
- Export ra để các file khác dùng

**Usage:**
```python
from app.core.http import SESSION, TIMEOUT

response = SESSION.post(
    url="https://api.groq.com/...",
    json={...},
    timeout=TIMEOUT  # ← 120 giây
)
```

**Tại sao cần timeout?**
- Tránh request "treo" mãi mãi
- Nếu Groq API down, sau 120s sẽ raise `requests.exceptions.Timeout`

---

## 🎯 Tổng kết flow hoạt động

### Scenario 1: Request thành công ngay

```
1. Code gọi: SESSION.post("https://api.groq.com/...", timeout=TIMEOUT)
2. HTTPAdapter make request
3. Response: 200 OK
4. Return response ✅
```

**Timeline:** ~500ms (latency bình thường của Groq)

---

### Scenario 2: Temporary failure → Retry success

```
1. Request #1 → Response: 503 Service Unavailable
   ↓
2. Retry logic check: 503 in status_forcelist? YES
   ↓
3. Wait 0.5 seconds (backoff_factor * 2^0)
   ↓
4. Request #2 → Response: 200 OK ✅
   ↓
5. Return response
```

**Timeline:** ~1.5s (500ms + 500ms wait + 500ms)

**User experience:** Không thấy lỗi, chỉ chậm hơn 1 chút

---

### Scenario 3: Persistent failure → All retries failed

```
1. Request #1 → 503 (wait 0.5s)
2. Request #2 → 503 (wait 1.0s)
3. Request #3 → 503 (wait 2.0s)
4. Request #4 → 503
   ↓
5. Raise requests.exceptions.RetryError ❌
```

**Timeline:** ~5.5s (500ms × 4 + 0.5s + 1.0s + 2.0s)

**Handler code:**
```python
try:
    response = SESSION.post(...)
except requests.exceptions.RetryError:
    return {"error": "Groq API unavailable after retries"}
```

---

### Scenario 4: Client error (no retry)

```
1. Request #1 → Response: 401 Unauthorized
   ↓
2. Retry logic check: 401 in status_forcelist? NO
   ↓
3. Return response immediately (no retry) ❌
```

**Timeline:** ~500ms (không waste time retry lỗi không fix được)

---

## 🔄 Comparison: With vs Without Retry

### Without Retry (naive approach):

```python
import requests

response = requests.post("https://api.groq.com/...")
# Nếu fail → Lỗi ngay, user thấy error
```

**Problems:**
- Groq API có thể temporary down vài giây
- Network blip → Request fail
- User experience kém (thấy lỗi thay vì chờ retry)

---

### With Retry (our approach):

```python
from app.core.http import SESSION, TIMEOUT

response = SESSION.post(
    "https://api.groq.com/...",
    timeout=TIMEOUT
)
# Nếu fail → Tự động retry 3 lần
# User chỉ thấy chậm hơn, không thấy lỗi (nếu retry success)
```

**Benefits:**
- ✅ Resilient to temporary failures
- ✅ Better user experience
- ✅ Higher success rate

---

## 📊 Diagram: Retry Flow

```
┌──────────────────────────────────────────────────────────┐
│           SESSION.post("https://api.groq.com/")          │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ↓
         ┌────────────────────────────┐
         │  HTTPAdapter (with Retry)  │
         └────────────┬───────────────┘
                      │
                      ↓
              ┌───────────────┐
              │  HTTP Request │
              └───────┬───────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ↓                           ↓
   [200 OK]                    [503 Error]
        │                           │
        │                           ↓
        │                   ┌───────────────────┐
        │                   │ Check forcelist:  │
        │                   │ 503 in (429,502,  │
        │                   │ 503,504)? YES     │
        │                   └───────┬───────────┘
        │                           │
        │                           ↓
        │                   Wait 0.5 seconds
        │                           │
        │                           ↓
        │                   Retry Request #2
        │                           │
        │                   ┌───────┴────────┐
        │                   │                │
        │                   ↓                ↓
        │              [200 OK]         [503 Error]
        │                   │                │
        │                   │         (Retry #3, wait 1.0s)
        │                   │                │
        ↓                   ↓                ↓
   Return Response    Return Response   Continue until
                                        total=3 retries
```

---

## 💡 Những điểm quan trọng khi thuyết trình

### 1. Tại sao cần retry logic?

**Real-world scenario:**
```
User typing code → Extension call backend → Backend call Groq
                                                  ↓
                                            Groq API timeout
                                            (datacenter blip)
                                                  ↓
                                          Without retry: ❌ Error shown
                                          With retry: ✅ Success after 1s
```

### 2. Exponential backoff là gì?

**Visual:**
```
Retry 1: |━━|           (0.5s)
Retry 2: |━━━━|         (1.0s)
Retry 3: |━━━━━━━━|     (2.0s)

Càng retry nhiều, càng chờ lâu
→ Cho server thời gian recover
```

### 3. Status code nào nên retry?

**✅ Should retry:**
- 429: Rate limit (sẽ reset sau vài giây)
- 5xx: Server errors (temporary issues)

**❌ Should NOT retry:**
- 4xx: Client errors (request sai, retry cũng fail)

### 4. Connection pooling benefit?

**Without Session:**
```python
for i in range(100):
    requests.post(...)  # Mở 100 TCP connections mới
# Tốn thời gian handshake (SSL/TLS) mỗi lần
```

**With Session:**
```python
session = requests.Session()
for i in range(100):
    session.post(...)  # Tái sử dụng connection
# Chỉ handshake 1 lần, nhanh hơn 50-70%
```

---

## 🧪 Test Cases

### Test 1: Normal request (no retry needed)

```python
from app.core.http import SESSION, TIMEOUT

response = SESSION.get("https://httpbin.org/status/200")
print(response.status_code)  # 200
# No retries triggered
```

---

### Test 2: Retry on 503

```python
# httpbin.org/status/503 returns 503 error
response = SESSION.get(
    "https://httpbin.org/status/503",
    timeout=TIMEOUT
)
# Internally:
# - Attempt 1: 503
# - Wait 0.5s
# - Attempt 2: 503
# - Wait 1.0s
# - Attempt 3: 503
# - Wait 2.0s
# - Attempt 4: 503
# Finally raises RetryError after 3 retries
```

---

### Test 3: No retry on 404

```python
response = SESSION.get("https://httpbin.org/status/404")
print(response.status_code)  # 404 (immediate, no retries)
# 404 not in status_forcelist → No retry
```

---

## 🔧 Customization Options

**Nếu muốn thay đổi retry behavior:**

```python
# Nhiều retries hơn (5 lần thay vì 3):
retry = Retry(total=5, backoff_factor=0.5, ...)

# Chờ lâu hơn (1 giây base):
retry = Retry(total=3, backoff_factor=1.0, ...)
# → Wait times: 1s, 2s, 4s

# Retry thêm 408 (Request Timeout):
retry = Retry(
    total=3,
    status_forcelist=(408, 429, 502, 503, 504),
    ...
)
```

---

**File này hoàn tất!** Tiếp theo tôi sẽ giải thích `logging.py`. Bạn muốn tôi tiếp tục không?
