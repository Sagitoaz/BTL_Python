# Giải thích chi tiết: `server/app/core/logging.py`

## 📋 Mục đích của file

File này setup **logging system** cho toàn bộ backend. Mỗi log message sẽ tự động có **request_id** để dễ dàng trace 1 request qua nhiều layers.

## 🔍 Phân tích từng dòng code

### Import statements

```python
# server/core/logging.py
import logging

from app.middleware.request_id import RequestIdFilter
```

**Giải thích:**

**`import logging`**
- Module built-in của Python để ghi logs
- Không cần install thêm

**`from app.middleware.request_id import RequestIdFilter`**
- Custom filter để gắn request_id vào mỗi log record
- RequestIdFilter sẽ được giải thích chi tiết sau

---

## 🎯 Function: `setup_logging()`

```python
def setup_logging(level=logging.INFO):
```

**Giải thích:**
- Function để config logging cho toàn bộ app
- `level=logging.INFO`: Mặc định log từ INFO trở lên

**Log levels (từ thấp đến cao):**
```
DEBUG (10)    → Chi tiết nhất, dùng khi debug
INFO (20)     → Thông tin general (default)
WARNING (30)  → Cảnh báo, không critical
ERROR (40)    → Lỗi nghiêm trọng
CRITICAL (50) → Lỗi hệ thống, app có thể crash
```

**Ví dụ:**
```python
logging.debug("Variable x = 5")           # Chỉ hiện khi level=DEBUG
logging.info("Request received")          # Hiện khi level=INFO
logging.warning("API rate limit 80%")     # Hiện khi level=WARNING
logging.error("Groq API failed")          # Luôn hiện (ERROR >= INFO)
logging.critical("Database down!")        # Luôn hiện (CRITICAL >= INFO)
```

---

### Configure Basic Logging

```python
    logging.basicConfig(
        # Quan trong: them request_id vao format de hien thi trong log
        format="%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
        level=level,
    )
```

**Phân tích từng phần:**

#### `logging.basicConfig(...)`

**Giải thích:**
- Config global logging settings cho toàn app
- Chỉ nên gọi 1 lần duy nhất khi app khởi động

---

#### `format="..."`

**Log format string với placeholders:**

```python
format="%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"
```

**Phân tích từng placeholder:**

**`%(asctime)s`**
- Timestamp của log message
- Format mặc định: `2025-11-11 14:23:45,123`
- `s` = string format

**Ví dụ output:**
```
2025-11-11 14:23:45,123
```

---

**`[%(levelname)s]`**
- Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Nằm trong `[]` để dễ nhìn

**Ví dụ output:**
```
[INFO]
[ERROR]
[WARNING]
```

---

**`[%(request_id)s]`** ← **QUAN TRỌNG NHẤT**

**Giải thích:**
- UUID unique cho mỗi HTTP request
- Được gắn bởi `RequestIdFilter` (giải thích phía dưới)
- Cho phép trace tất cả logs của 1 request

**Tại sao cần request_id?**

**Scenario: Production server với 100 requests đồng thời**

```python
# WITHOUT request_id (confusing):
2025-11-11 14:23:45 [INFO] Starting completion
2025-11-11 14:23:45 [INFO] Starting completion  # ← Request nào?
2025-11-11 14:23:46 [INFO] Calling Groq API
2025-11-11 14:23:46 [INFO] Calling Groq API     # ← Request nào?
2025-11-11 14:23:47 [INFO] Response sent
2025-11-11 14:23:47 [ERROR] Groq API failed     # ← Request nào bị lỗi?
```

**Không biết log nào thuộc request nào!**

---

```python
# WITH request_id (clear):
2025-11-11 14:23:45 [INFO] [abc-123] Starting completion
2025-11-11 14:23:45 [INFO] [def-456] Starting completion  # ← Request khác
2025-11-11 14:23:46 [INFO] [abc-123] Calling Groq API
2025-11-11 14:23:46 [INFO] [def-456] Calling Groq API
2025-11-11 14:23:47 [INFO] [abc-123] Response sent ✅
2025-11-11 14:23:47 [ERROR] [def-456] Groq API failed ❌  # ← Biết ngay request def-456 lỗi
```

**Dễ dàng grep logs của 1 request:**
```bash
grep "abc-123" server.log
# → Xem toàn bộ lifecycle của request abc-123
```

---

**`%(name)s`**
- Tên của logger (thường là module name)
- Ví dụ: `app.routers.completions`, `app.services.groq`

**Usage trong code:**
```python
# completions.py
logger = logging.getLogger(__name__)
# → __name__ = "app.routers.completions"

logger.info("Processing request")
# Output: ... [abc-123] app.routers.completions: Processing request
```

---

**`: %(message)s`**
- Nội dung chính của log message
- Dev viết gì thì hiện đó

**Ví dụ:**
```python
logger.info("User submitted code completion request")
# → message = "User submitted code completion request"
```

---

#### **Full log output example:**

```python
logger.info("Groq API returned 250 tokens")
```

**Output:**
```
2025-11-11 14:23:45,123 [INFO] [abc-123] app.services.groq: Groq API returned 250 tokens
│                        │      │         │                   │
│                        │      │         │                   └─ Message
│                        │      │         └─ Logger name
│                        │      └─ Request ID (UUID)
│                        └─ Log level
└─ Timestamp
```

---

#### `level=level`

**Giải thích:**
- Set minimum log level
- Default: `logging.INFO` (từ parameter)

**Filter behavior:**
```python
# Nếu level=INFO:
logging.debug("Debug info")      # ❌ Không hiện (DEBUG < INFO)
logging.info("Request received")  # ✅ Hiện (INFO >= INFO)
logging.error("API failed")      # ✅ Hiện (ERROR > INFO)

# Nếu level=DEBUG (development):
logging.debug("Variable x = 5")  # ✅ Hiện tất cả
```

---

### Add Request ID Filter

```python
    # Thêm filter để gắn request_id vào mỗi log record
    # getlogger tra ve mot doi tuong logger
    logging.getLogger().addFilter(RequestIdFilter())
```

**Phân tích từng dòng:**

#### `logging.getLogger()`

**Giải thích:**
- Lấy **root logger** (logger gốc)
- Không truyền tên → Return root logger
- Root logger là cha của tất cả loggers khác

**Logger hierarchy:**
```
Root logger
  │
  ├─ app.routers.completions
  ├─ app.services.groq
  └─ app.core.postprocess
```

**Tại sao modify root logger?**
- Filter áp dụng cho TẤT CẢ child loggers
- Chỉ cần thêm filter 1 lần, tất cả modules đều có request_id

---

#### `.addFilter(RequestIdFilter())`

**Giải thích:**
- Thêm custom filter vào logger
- `RequestIdFilter()`: Tạo instance của filter class

**RequestIdFilter làm gì?** (Chi tiết trong `middleware/request_id.py`):

```python
# Simplified version
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        # Lấy request_id từ context (ContextVar)
        request_id = get_current_request_id()
        
        # Gắn vào log record
        record.request_id = request_id or "no-request"
        
        return True  # Cho phép log hiển thị
```

**Flow:**
```
1. Code viết: logger.info("Processing request")
2. Logging system tạo LogRecord object
3. Filter.filter(record) được gọi
4. Filter gắn: record.request_id = "abc-123"
5. Format string dùng %(request_id)s → "abc-123"
6. Output: "... [abc-123] ... Processing request"
```

---

## 🎯 How It Works: Full Flow

### Step 1: App Startup

```python
# main.py
from app.core.logging import setup_logging

setup_logging(level=logging.INFO)
# → Logging system ready
```

---

### Step 2: Request Arrives

```python
# Request comes in with X-Request-ID header
POST /complete
Headers:
  X-Request-ID: abc-123-def-456
  Authorization: Bearer 5conmeo
Body: {"prefix": "def add(", ...}
```

---

### Step 3: Middleware Sets Request ID

```python
# middleware/request_id.py (runs first)
request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
# → request_id = "abc-123-def-456"

# Store in context var (thread-safe global)
set_current_request_id(request_id)
```

---

### Step 4: Handler Logs Messages

```python
# routers/completions.py
logger = logging.getLogger(__name__)

logger.info("Processing completion request")
# ↓
# LogRecord created
# ↓
# RequestIdFilter.filter() called
# → record.request_id = "abc-123-def-456" (from context)
# ↓
# Format string interpolated
# ↓
# Output: 2025-11-11 14:23:45 [INFO] [abc-123-def-456] app.routers.completions: Processing completion request
```

---

### Step 5: Multiple Layers Log

```python
# completions.py
logger.info("Calling Groq API")
# → [abc-123-def-456] app.routers.completions: Calling Groq API

# groq.py
groq_logger.info("Sending prompt to llama-3.3-70b")
# → [abc-123-def-456] app.services.groq: Sending prompt to llama-3.3-70b

# groq.py
groq_logger.info("Received 250 tokens")
# → [abc-123-def-456] app.services.groq: Received 250 tokens

# completions.py
logger.info("Postprocessing completion")
# → [abc-123-def-456] app.routers.completions: Postprocessing completion
```

**Tất cả logs có cùng request_id!**

---

### Step 6: Response Sent

```python
logger.info("Response sent successfully")
# → [abc-123-def-456] app.routers.completions: Response sent successfully
```

---

### Step 7: Debug a Specific Request

```bash
# Production server logs
cat server.log | grep "abc-123-def-456"

# Output:
2025-11-11 14:23:45 [INFO] [abc-123-def-456] app.routers.completions: Processing completion request
2025-11-11 14:23:45 [INFO] [abc-123-def-456] app.services.groq: Sending prompt to llama-3.3-70b
2025-11-11 14:23:46 [INFO] [abc-123-def-456] app.services.groq: Received 250 tokens
2025-11-11 14:23:46 [INFO] [abc-123-def-456] app.routers.completions: Postprocessing completion
2025-11-11 14:23:46 [INFO] [abc-123-def-456] app.routers.completions: Response sent successfully

# → Complete request trace! ✅
```

---

## 📊 Diagram: Logging Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    App Startup                              │
│  setup_logging(level=INFO)                                 │
│    ↓                                                        │
│  logging.basicConfig(format="... [%(request_id)s] ...")    │
│    ↓                                                        │
│  logging.getLogger().addFilter(RequestIdFilter())          │
└────────────────────────┬───────────────────────────────────┘
                         │
                         │ Logging system ready
                         ↓
┌────────────────────────────────────────────────────────────┐
│              HTTP Request Arrives                           │
│  POST /complete                                            │
│  X-Request-ID: abc-123                                     │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────┐
│              Middleware (RequestIdMiddleware)               │
│  request_id = "abc-123"                                    │
│  set_current_request_id(request_id)  # Store in context    │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────┐
│               Handler Logs Message                          │
│  logger.info("Processing request")                         │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────┐
│              RequestIdFilter.filter()                       │
│  request_id = get_current_request_id()  # "abc-123"        │
│  record.request_id = request_id                            │
│  return True                                               │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────┐
│              Format String Applied                          │
│  "%(asctime)s [%(levelname)s] [%(request_id)s] ..."        │
│  → "2025-11-11 14:23:45 [INFO] [abc-123] ... message"      │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
                    Print to stdout
              (Render.com captures logs)
```

---

## 💡 Những điểm quan trọng khi thuyết trình

### 1. Tại sao cần logging?

**Debugging trong production:**
```python
# Code fails in production but works in development
# Logs giúp biết:
# - Request nào bị lỗi?
# - Ở bước nào bị lỗi?
# - Input là gì?
# - Output là gì?
```

**Monitoring:**
```bash
# Xem performance
grep "Response sent" server.log | wc -l
# → Số requests processed today

# Tìm lỗi
grep "ERROR" server.log
# → Tất cả errors
```

---

### 2. Request ID là gì và tại sao cần?

**Problem:** Trong production, có thể 100 requests đồng thời. Logs bị trộn lẫn.

**Solution:** Mỗi request có unique ID (UUID), gắn vào mọi log của request đó.

**Benefits:**
```bash
# Trace 1 request từ đầu đến cuối
grep "abc-123" server.log

# Tính latency của 1 request
grep "abc-123" server.log | head -1  # Start time
grep "abc-123" server.log | tail -1  # End time
```

---

### 3. Log levels khi nào dùng gì?

**DEBUG:** Development only
```python
logger.debug(f"Variable x = {x}, y = {y}")
logger.debug(f"Function foo() called with args: {args}")
```

**INFO:** General flow
```python
logger.info("User request received")
logger.info("Groq API called successfully")
logger.info("Response sent")
```

**WARNING:** Non-critical issues
```python
logger.warning("API rate limit 80% used")
logger.warning("black formatter not installed, skipping format")
```

**ERROR:** Actual errors
```python
logger.error("Groq API returned 500")
logger.error("Failed to postprocess completion")
```

**CRITICAL:** System-level failures
```python
logger.critical("Database connection lost")
logger.critical("Out of memory")
```

---

### 4. ContextVar cho request_id

**Problem:** Làm sao pass request_id vào mọi function mà không thêm parameter?

```python
# Bad: Pass request_id everywhere
def complete(request, request_id):
    result = call_groq(request, request_id)
    postprocess(result, request_id)
    ...

# Good: Use ContextVar (thread-safe global)
set_current_request_id(request_id)  # Set once in middleware
# Mọi function tự động access được
```

**ContextVar:** Python 3.7+ feature cho async-safe context storage

---

## 🧪 Test Logging

### Test 1: Basic logging

```python
# test_logging.py
import logging
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

logger.info("Test message")
# Output: 2025-11-11 14:23:45,123 [INFO] [no-request] __main__: Test message
#                                        └─ No request context yet
```

---

### Test 2: With request ID

```python
from app.core.logging import setup_logging
from app.middleware.request_id import set_current_request_id
import logging

setup_logging()
logger = logging.getLogger(__name__)

# Simulate middleware setting request_id
set_current_request_id("test-abc-123")

logger.info("Processing request")
# Output: 2025-11-11 14:23:45 [INFO] [test-abc-123] __main__: Processing request
#                                    └─ request_id present!
```

---

### Test 3: Multiple requests (async)

```python
import asyncio
import logging
from app.core.logging import setup_logging
from app.middleware.request_id import set_current_request_id

setup_logging()
logger = logging.getLogger(__name__)

async def handle_request(request_id):
    set_current_request_id(request_id)
    logger.info(f"Request {request_id} started")
    await asyncio.sleep(0.1)
    logger.info(f"Request {request_id} finished")

# Simulate 3 concurrent requests
async def main():
    await asyncio.gather(
        handle_request("req-1"),
        handle_request("req-2"),
        handle_request("req-3"),
    )

asyncio.run(main())

# Output (interleaved but traceable):
# [INFO] [req-1] ... Request req-1 started
# [INFO] [req-2] ... Request req-2 started
# [INFO] [req-3] ... Request req-3 started
# [INFO] [req-1] ... Request req-1 finished
# [INFO] [req-2] ... Request req-2 finished
# [INFO] [req-3] ... Request req-3 finished
```

---

## 🔧 Production Best Practices

### 1. Log to file in production

```python
# Add file handler
file_handler = logging.FileHandler("server.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s")
)
logging.getLogger().addHandler(file_handler)
```

---

### 2. Rotate logs (avoid huge files)

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "server.log",
    maxBytes=10_000_000,  # 10MB
    backupCount=5  # Keep 5 old files
)
# Files: server.log, server.log.1, server.log.2, ...
```

---

### 3. Structured logging (JSON format)

```python
import json

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "request_id": getattr(record, "request_id", "no-request"),
            "logger": record.name,
            "message": record.getMessage()
        }
        return json.dumps(log_data)

# Output: {"timestamp": "...", "level": "INFO", "request_id": "abc-123", ...}
# → Easy to parse with tools like Elasticsearch, Splunk
```

---

**File này hoàn tất!** Tiếp theo: `security.py` (API key validation). Tiếp tục nhé? 🚀
