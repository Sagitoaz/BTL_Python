# Giải thích chi tiết: `server/app/middleware/request_id.py`

## 📋 Mục đích của file

File này implement **Request ID Middleware** để:
1. **Gắn unique ID** cho mỗi HTTP request
2. **Track requests** qua nhiều layers (routing, services, logging)
3. **Thêm request_id vào logs** tự động

---

## 🔍 Phân tích từng phần

### Import statements

```python
import logging
import uuid

from fastapi import Request, Response

from app.core.config import settings
```

**Giải thích:**

- `logging`: Để tạo logging filter
- `uuid`: Generate unique IDs (UUID4)
- `Request, Response`: FastAPI types cho HTTP request/response
- `settings`: Lấy config (`REQUEST_ID`, `HEADERS_MIDDLEWARE`)

---

## 🎯 Class: `RequestIdFilter`

### Mục đích
Logging filter để **tự động gắn request_id** vào mọi log record

### Code

```python
# Filter để thêm field request_id vào log record
# log la ghi chep cac su kien xay ra trong qua trinh chay ung dung
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        # Neu khong co request_id thi them vao
        if not hasattr(record, settings.REQUEST_ID):
            record.request_id = "-"
        return True
```

---

### Phân tích chi tiết

#### `class RequestIdFilter(logging.Filter):`

**Giải thích:**
- Kế thừa từ `logging.Filter`
- Filter được gọi cho **MỌI** log message trước khi xuất ra

---

#### `def filter(self, record):`

**Parameters:**
- `record`: `LogRecord` object chứa thông tin về log message
- `record.msg`: Nội dung message
- `record.levelname`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Custom attributes có thể thêm vào: `record.request_id`, etc.

---

#### `if not hasattr(record, settings.REQUEST_ID):`

**Logic:**
- `settings.REQUEST_ID` = `"request_id"` (từ config)
- `hasattr(record, "request_id")`: Check xem record có attribute `request_id` chưa?

**Khi nào có?**
```python
# Đã set trong context (contextvars)
# Hoặc manual: logger.info("msg", extra={"request_id": "abc"})
```

**Khi nào KHÔNG có?**
```python
# Log ngoài request context (startup, background tasks)
# Filter sẽ gắn default value
```

---

#### `record.request_id = "-"`

**Giải thích:**
- Gắn default value `"-"` nếu không có request_id
- Tránh error khi format string có `%(request_id)s`

**Output example:**
```
# With request_id:
2025-11-11 14:23:45 [INFO] [abc-123] app.routers.completions: Processing

# Without request_id (background task):
2025-11-11 14:23:45 [INFO] [-] app.core.scheduler: Running cleanup
```

---

#### `return True`

**Giải thích:**
- `True`: Cho phép log hiển thị (không filter out)
- `False`: Chặn log (không xuất)

**Use case cho `return False`:**
```python
class SensitiveFilter(logging.Filter):
    def filter(self, record):
        # Block logs chứa "password"
        if "password" in record.msg.lower():
            return False  # Don't log!
        return True
```

---

## 🔄 Async Function: `request_id_middleware()`

### Mục đích
**Middleware chính** - Wrap mỗi HTTP request với request_id logic

### Function Signature

```python
# Middleware nhu mot bo loc trung gian giua request va response
# Middleware chính
# Ham async de xu ly bat dong bo ( nhieu ham async trong ung dung)
async def request_id_middleware(request: Request, call_next):
```

**Giải thích:**

#### `async def`
- Async function (non-blocking)
- FastAPI middleware phải là async

#### Parameters

**`request: Request`**
- FastAPI Request object
- Chứa headers, body, query params, etc.

**`call_next`**
- Callable để gọi handler tiếp theo trong chain
- Signature: `call_next(request) -> Response`

---

### Step 1: Extract or Generate Request ID

```python
    # Lấy từ header nếu có, không thì tạo mới
    # uuid la mot chuoi ky tu duy nhat
    rid = request.headers.get(settings.HEADERS_MIDDLEWARE, str(uuid.uuid4()))
```

**Phân tích:**

#### `request.headers.get(settings.HEADERS_MIDDLEWARE, ...)`

**`settings.HEADERS_MIDDLEWARE`:**
- Value: `"X-Request-ID"` (từ config.py)
- Standard HTTP header name cho request tracking

**`.get(key, default)`:**
- Lấy header value nếu có
- Return default nếu không có

**Example requests:**

**Request có header:**
```http
POST /complete HTTP/1.1
X-Request-ID: client-generated-abc-123
...

# rid = "client-generated-abc-123" ✅
```

**Request KHÔNG có header:**
```http
POST /complete HTTP/1.1
...

# rid = str(uuid.uuid4()) 
# → "550e8400-e29b-41d4-a716-446655440000" ✅
```

---

#### `str(uuid.uuid4())`

**`uuid.uuid4()`:**
- Generate random UUID (version 4)
- 128-bit number
- Format: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`

**Example outputs:**
```python
uuid.uuid4()  # UUID('550e8400-e29b-41d4-a716-446655440000')
str(uuid.uuid4())  # "550e8400-e29b-41d4-a716-446655440000"
```

**Tại sao UUID4?**
- Globally unique (collision probability ~0)
- No coordination needed (random)
- 122 random bits → 5.3×10³⁶ possible values

---

### Step 2: Store in Request State

```python
    # gan request_id vao request.state de su dung sau nay
    request.state.request_id = rid
```

**Giải thích:**

#### `request.state`

**What is it?**
- Mutable namespace để attach arbitrary data vào request
- Accessible trong tất cả handlers và dependencies
- Scoped to this request only (thread-safe)

**Example usage:**
```python
# Middleware sets:
request.state.request_id = "abc-123"
request.state.user_id = "user-456"

# Handler accesses:
@app.get("/profile")
async def profile(request: Request):
    print(request.state.request_id)  # "abc-123"
    print(request.state.user_id)     # "user-456"
```

**Tại sao không dùng global variable?**
```python
# BAD (not thread-safe):
global current_request_id
current_request_id = rid  # Race condition with concurrent requests!

# GOOD (request-scoped):
request.state.request_id = rid  # Each request has own state ✅
```

---

### Step 3: Call Next Handler (try-except-finally)

```python
    try:
        # Goi ham call_next de tiep tuc xu ly request(xu li nhieu request cung luc)
        response: Response = await call_next(request)
    except Exception:
        raise
    finally:
        # Nếu đã có response object, thêm header (nếu chưa gửi)
        try:
            # Them request_id vao header cua response
            if "response" in locals():
                response.headers[settings.HEADERS_MIDDLEWARE] = rid
        except Exception:
            # Nếu không thể gắn (vd: header đã gửi), bỏ qua.
            pass
    return response
```

---

#### Try block: Call next handler

```python
    try:
        response: Response = await call_next(request)
```

**`await call_next(request)`:**
- Gọi handler tiếp theo trong middleware chain
- Hoặc route handler nếu đây là middleware cuối
- Return `Response` object

**Flow:**
```
request_id_middleware
    ↓
call_next(request)
    ↓
Other middlewares (if any)
    ↓
Route handler: @app.post("/complete")
    ↓
Generate response
    ↓
Return to middleware
    ↓
Continue...
```

---

#### Except block: Re-raise exception

```python
    except Exception:
        raise
```

**Tại sao catch rồi re-raise?**
- Để execute `finally` block (thêm header)
- Sau đó propagate exception lên FastAPI error handler

**Without this:**
```python
# NO except block:
try:
    response = await call_next(request)
finally:
    ...

# Problem: Exception bỏ qua finally block trong một số cases
```

---

#### Finally block: Add response header

```python
    finally:
        try:
            if "response" in locals():
                response.headers[settings.HEADERS_MIDDLEWARE] = rid
        except Exception:
            pass
```

**Phân tích:**

#### `if "response" in locals():`

**`locals()`:**
- Dictionary của local variables trong scope hiện tại
- VD: `{"request": <Request>, "rid": "abc-123", "response": <Response>}`

**Check `"response" in locals()`:**
- `True`: `response = await call_next()` đã execute thành công
- `False`: Exception xảy ra trước khi gán response

**Tại sao cần check?**
```python
# Scenario 1: Success
response = await call_next(request)  # response assigned ✅
finally:
    if "response" in locals():  # True
        response.headers[...] = rid  # Works!

# Scenario 2: Early exception
raise ValueError("Error before call_next")  # response NEVER assigned
finally:
    if "response" in locals():  # False
        # Skip (tránh NameError: response not defined)
```

---

#### `response.headers[settings.HEADERS_MIDDLEWARE] = rid`

**Giải thích:**
- Thêm `X-Request-ID` header vào response
- Client có thể dùng để correlate request/response

**Example response:**
```http
HTTP/1.1 200 OK
X-Request-ID: abc-123
Content-Type: application/json

{"completion": "return a + b"}
```

**Use case client-side:**
```typescript
// Client send request
const response = await fetch('/complete', {
    headers: {'X-Request-ID': 'client-abc-123'}
});

// Server echo back in response
console.log(response.headers.get('X-Request-ID')); 
// → "client-abc-123"

// Client can verify: same ID = same request ✅
```

---

#### Nested try-except (safety)

```python
        try:
            if "response" in locals():
                response.headers[...] = rid
        except Exception:
            pass
```

**Tại sao cần nested try?**

**Possible exceptions:**
```python
# 1. Headers already sent (streaming response)
response.headers[...] = rid  # RuntimeError: Headers already sent

# 2. Response is StreamingResponse (no .headers attribute)
response.headers[...] = rid  # AttributeError

# 3. Header value invalid
response.headers[...] = None  # TypeError
```

**Catch all và ignore:**
```python
except Exception:
    pass  # Don't crash the request just because header can't be added
```

**Priority:** Return response > Add header

---

### Step 4: Return Response

```python
    return response
```

**Flow complete:**
```
1. Request arrives
2. Middleware extracts/generates request_id
3. Store in request.state
4. Call next handler
5. Add request_id to response headers
6. Return response to client
```

---

## 📊 Diagram: Middleware Flow

```
┌────────────────────────────────────────────────────────────┐
│                    Client Request                           │
│  POST /complete                                            │
│  X-Request-ID: client-abc-123 (optional)                   │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────┐
│              request_id_middleware()                        │
│                                                            │
│  1. Extract request_id:                                    │
│     rid = request.headers.get("X-Request-ID")             │
│     → Found: "client-abc-123"                             │
│     → Not found: Generate uuid.uuid4()                    │
│                                                            │
│  2. Store in request state:                                │
│     request.state.request_id = rid                        │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓ await call_next(request)
┌────────────────────────────────────────────────────────────┐
│              Route Handler                                  │
│  @app.post("/complete")                                    │
│  async def complete(request):                              │
│      # Access request_id:                                  │
│      rid = request.state.request_id                       │
│      logger.info(f"[{rid}] Processing...")                │
│      ...                                                   │
│      return {"completion": "..."}                          │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓ Returns Response
┌────────────────────────────────────────────────────────────┐
│              request_id_middleware() (finally block)        │
│                                                            │
│  3. Add to response headers:                               │
│     response.headers["X-Request-ID"] = rid                │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────┐
│                    Response to Client                       │
│  HTTP/1.1 200 OK                                           │
│  X-Request-ID: client-abc-123                              │
│  {"completion": "return a + b"}                            │
└────────────────────────────────────────────────────────────┘
```

---

## 🔗 Integration với Logging

### RequestIdFilter + Middleware

**Setup trong `main.py`:**

```python
# main.py
from fastapi import FastAPI
from app.core.logging import setup_logging
from app.middleware.request_id import request_id_middleware

# Setup logging (adds RequestIdFilter)
setup_logging()

app = FastAPI()

# Add middleware
app.middleware("http")(request_id_middleware)
```

---

### Complete Flow với Logging

```python
# Request comes in
POST /complete
X-Request-ID: req-abc-123

# ↓ Middleware runs
request.state.request_id = "req-abc-123"

# ↓ Handler logs
logger = logging.getLogger(__name__)
logger.info("Processing completion request")

# ↓ RequestIdFilter.filter() called
def filter(self, record):
    # Get request_id from... where?
    # Problem: record doesn't have access to request.state!
```

**🤔 Wait, có vấn đề!**

**RequestIdFilter cần access request_id, nhưng LogRecord không có request.state!**

**Solution: ContextVar (Python 3.7+)**

---

### Missing Piece: ContextVar

**File này thiếu implementation của ContextVar!**

**Cần thêm:**

```python
# request_id.py (missing in current code)
from contextvars import ContextVar

# Thread-safe storage for request_id
_request_id_context: ContextVar[str] = ContextVar('request_id', default='-')

def get_current_request_id() -> str:
    """Get request_id from current context"""
    return _request_id_context.get()

def set_current_request_id(request_id: str):
    """Set request_id for current context"""
    _request_id_context.set(request_id)
```

**Updated middleware:**

```python
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get(settings.HEADERS_MIDDLEWARE, str(uuid.uuid4()))
    request.state.request_id = rid
    
    # ← ADD THIS: Set in context for logging
    set_current_request_id(rid)
    
    try:
        response = await call_next(request)
    ...
```

**Updated filter:**

```python
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        # Get from context instead of hasattr check
        record.request_id = get_current_request_id()
        return True
```

**Now it works!**

---

## 💡 Key Points cho thuyết trình

### 1. Request ID để làm gì?

**Distributed tracing:**
```
Client → Backend → Groq API → Database
  |         |          |          |
  All logs có cùng request_id = "abc-123"
  → Easy to trace entire request flow!
```

**Debugging:**
```bash
# User report lỗi với request_id
curl /complete → Response header: X-Request-ID: xyz-789

# Admin debug:
grep "xyz-789" server.log
# → See all logs của request đó
```

---

### 2. Middleware pattern

**Middleware = Onion layers:**
```
             ┌────────────────────┐
             │   Middleware 1     │ ← Outer
          ┌──┤ (request_id)       │
          │  └────────────────────┘
          │
          │  ┌────────────────────┐
          │  │   Middleware 2     │ ← Middle
          │┌─┤ (auth)             │
          ││ └────────────────────┘
          ││
          ││ ┌────────────────────┐
          ││ │   Route Handler    │ ← Core
          ││ │ /complete          │
          ││ └────────────────────┘
          ││         │
          │└─────────┘
          └───────────┘
```

**Execution order:**
```
Request: 1 → 2 → Handler → 2 → 1 → Response
```

---

### 3. request.state pattern

**Scope-safe data passing:**

```python
# ✅ Good: request.state (scoped to request)
@app.middleware("http")
async def middleware(request, call_next):
    request.state.data = "abc"
    return await call_next(request)

@app.get("/test")
async def handler(request: Request):
    print(request.state.data)  # "abc" ✅

# ❌ Bad: global variable (race condition)
current_data = None

@app.middleware("http")
async def middleware(request, call_next):
    global current_data
    current_data = "abc"  # ← Request A sets this
    # Request B arrives here, overwrites!
    return await call_next(request)
```

---

### 4. try-except-finally pattern

**Ensure cleanup:**
```python
try:
    response = await risky_operation()
except Exception:
    log_error()
    raise  # Re-raise để FastAPI handle
finally:
    cleanup()  # Always runs (success hoặc error)
```

---

### 5. UUID4 uniqueness

**Collision probability:**
- UUID4: 122 random bits
- Possible values: 2^122 = 5.3×10^36
- Generate 1 billion UUIDs/second
- Probability of collision: ~0% in lifetime of universe

---

## 🧪 Test Cases

### Test 1: Request với X-Request-ID header

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

response = client.post(
    "/complete",
    headers={"X-Request-ID": "test-abc-123"},
    json={"prefix": "def add(", "language": "python"}
)

# Check response header
assert response.headers["X-Request-ID"] == "test-abc-123" ✅
```

---

### Test 2: Request KHÔNG có header (auto-generate)

```python
response = client.post(
    "/complete",
    json={"prefix": "def add(", "language": "python"}
)

# Check có UUID format
request_id = response.headers["X-Request-ID"]
assert len(request_id) == 36  # UUID format: 8-4-4-4-12
assert request_id.count('-') == 4
```

---

### Test 3: request.state access

```python
from fastapi import Request

@app.get("/test")
async def test_handler(request: Request):
    # Access request_id set by middleware
    return {"request_id": request.state.request_id}

response = client.get("/test")
assert "request_id" in response.json()
```

---

## 🔧 Usage Example

**Complete integration:**

```python
# main.py
from fastapi import FastAPI
from app.middleware.request_id import request_id_middleware
from app.core.logging import setup_logging

setup_logging()  # Add RequestIdFilter
app = FastAPI()
app.middleware("http")(request_id_middleware)

# routers/completions.py
import logging
from fastapi import Request

logger = logging.getLogger(__name__)

@app.post("/complete")
async def complete(request: Request):
    # Log with request_id automatically
    logger.info("Processing completion")
    # → Output: [INFO] [abc-123] app.routers.completions: Processing completion
    
    # Access request_id if needed
    request_id = request.state.request_id
    
    return {"completion": "...", "request_id": request_id}
```

---

**File này hoàn tất!** Tiếp theo: `telemetry.py`. Tiếp tục không? 📊
