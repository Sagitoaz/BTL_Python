# Giải thích chi tiết: `server/app/core/security.py`

## 📋 Mục đích của file

File này implement **API key authentication** để bảo vệ backend khỏi truy cập trái phép. Chỉ clients có API key hợp lệ mới được gọi các endpoints.

## 🔍 Phân tích từng dòng code

### Import statements

```python
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
```

**Giải thích từng import:**

**`from fastapi import HTTPException, Security`**

- `HTTPException`: Class để throw HTTP errors (401, 403, 404, ...)
- `Security`: Dependency injection marker cho security schemes

**`from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer`**

- `HTTPBearer`: Security scheme cho Bearer token authentication
- `HTTPAuthorizationCredentials`: Object chứa credentials được extract từ request

**`from app.core.config import settings`**

- Import settings để lấy `API_KEY` (mặc định "5conmeo")

---

## 🔐 Security Scheme Setup

```python
security = HTTPBearer(auto_error=False)
```

**Phân tích:**

### `HTTPBearer`

**Giải thích:**
- FastAPI security scheme cho Bearer token authentication
- Bearer token format: `Authorization: Bearer <token>`
- Được dùng rộng rãi cho API authentication (OAuth 2.0, JWT)

**Ví dụ HTTP request:**
```http
POST /complete HTTP/1.1
Host: btl-python-r9kz.onrender.com
Authorization: Bearer 5conmeo
Content-Type: application/json

{"prefix": "def add(", "suffix": "", "language": "python"}
```

---

### `auto_error=False`

**Ý nghĩa:**
- `auto_error=False`: Không tự động raise error nếu token missing
- `auto_error=True` (default): Tự động raise 401 nếu không có token

**Tại sao dùng `False`?**
- Cho phép custom error handling trong function `require_api_key()`
- Có thể skip validation nếu `settings.API_KEY` rỗng (dev mode)

**So sánh:**

```python
# auto_error=True (strict):
security = HTTPBearer(auto_error=True)
# Request không có Authorization header → 401 Unauthorized ngay lập tức

# auto_error=False (flexible):
security = HTTPBearer(auto_error=False)
# Request không có Authorization → credentials = None
# Function decide xử lý thế nào
```

---

## 🔒 Function: `require_api_key()`

```python
def require_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),  # noqa: B008
):
```

**Phân tích:**

### Function signature

**`credentials: HTTPAuthorizationCredentials`**
- Parameter type: Object chứa scheme và credentials
- Structure:
  ```python
  HTTPAuthorizationCredentials(
      scheme="Bearer",  # "Bearer", "Basic", etc.
      credentials="5conmeo"  # Actual token
  )
  ```

---

### `= Security(security)`

**Giải thích:**
- `Security()`: FastAPI dependency injection marker
- `security`: HTTPBearer instance đã tạo ở trên
- FastAPI tự động:
  1. Parse `Authorization` header
  2. Extract token
  3. Pass vào function qua parameter `credentials`

**Flow magic của FastAPI:**
```python
# Request:
Authorization: Bearer 5conmeo

# FastAPI automatically:
1. See Security(security) dependency
2. Call security.__call__(request)
3. Parse "Bearer 5conmeo" → scheme="Bearer", credentials="5conmeo"
4. Inject HTTPAuthorizationCredentials object vào function
```

---

### `# noqa: B008`

**Giải thích:**
- Comment để disable flake8 warning B008
- B008: "Do not perform function calls in argument defaults"
- Lý do: `Security(security)` là function call, nhưng an toàn trong FastAPI context

**Tại sao B008 không quan trọng ở đây?**
- FastAPI's dependency injection system evaluate dependency mỗi request
- Không phải "mutable default argument" problem

---

## 🛡️ Validation Logic

### Check 1: API Key disabled (development mode)

```python
    if not settings.API_KEY:
        return
```

**Giải thích:**
- Nếu `API_KEY` rỗng trong config → Skip validation
- Return ngay (không check credentials)

**Use case:**
```bash
# Development .env
API_KEY=""  # Hoặc không set

# → Backend không yêu cầu authentication
# → Dễ test với curl, không cần header
```

**Example:**
```bash
# Works without Authorization header
curl -X POST http://localhost:9000/complete \
  -H "Content-Type: application/json" \
  -d '{"prefix": "def add(", "language": "python"}'
# ✅ Success (no auth required)
```

---

### Check 2: Missing or invalid scheme

```python
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing Bearer token")
```

**Phân tích:**

#### `if not credentials`

**Khi nào xảy ra?**
- Request không có `Authorization` header
- Hoặc header không match Bearer format

**Example requests triggering this:**
```http
# Case 1: No header
POST /complete HTTP/1.1
# → credentials = None

# Case 2: Wrong format
Authorization: 5conmeo  (missing "Bearer")
# → credentials = None

# Case 3: Wrong scheme
Authorization: Basic dXNlcjpwYXNz
# → credentials.scheme = "Basic" (not Bearer)
```

---

#### `credentials.scheme.lower() != "bearer"`

**Giải thích:**
- Extract scheme (phần trước token)
- Convert to lowercase để case-insensitive
- Check phải là "bearer"

**Valid schemes:**
```
Authorization: Bearer 5conmeo     ✅
Authorization: bearer 5conmeo     ✅ (lowercase OK)
Authorization: BEARER 5conmeo     ✅ (uppercase OK)
Authorization: Basic dXNlcjpwYXNz ❌ (wrong scheme)
```

---

#### `raise HTTPException(status_code=401, ...)`

**Giải thích:**
- Throw 401 Unauthorized error
- FastAPI tự động convert thành HTTP response:
  ```json
  {
    "detail": "Missing Bearer token"
  }
  ```

**HTTP response:**
```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{"detail": "Missing Bearer token"}
```

**Client (VS Code extension) nhận:**
```typescript
try {
    const response = await fetch('/complete', {...});
} catch (error) {
    // error.status = 401
    // error.body = {"detail": "Missing Bearer token"}
    console.error("Authentication failed");
}
```

---

### Check 3: Invalid token

```python
    if credentials.credentials != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid token")
```

**Phân tích:**

#### `credentials.credentials`

**Giải thích:**
- Actual token value (phần sau "Bearer")
- Example: `Authorization: Bearer 5conmeo` → credentials.credentials = "5conmeo"

---

#### `!= settings.API_KEY`

**Giải thích:**
- So sánh token với API key trong config
- settings.API_KEY = "5conmeo" (mặc định)

**Valid tokens:**
```bash
# .env
API_KEY=5conmeo

# Valid requests:
Authorization: Bearer 5conmeo ✅

# Invalid requests:
Authorization: Bearer wrong_key ❌
Authorization: Bearer 5conme0 ❌ (typo)
Authorization: Bearer 5conmeo123 ❌ (thêm ký tự)
```

---

#### `status_code=403` vs `401`

**Phân biệt:**

**401 Unauthorized:** "Bạn chưa authenticate"
- Missing token
- Wrong authentication scheme

**403 Forbidden:** "Bạn đã authenticate nhưng không có quyền"
- Token có nhưng sai
- Token đã expire
- Token không có permission

**Flow:**
```
No token → 401 (chưa đăng nhập)
Wrong token → 403 (đăng nhập sai)
Correct token → ✅ Allow
```

---

#### Error response

```json
{
  "detail": "Invalid token"
}
```

**Client handling:**
```typescript
if (response.status === 403) {
    showError("API key invalid. Check settings.");
}
```

---

## 🎯 How to Use: Dependency Injection

### Trong route handler:

```python
# routers/completions.py
from fastapi import APIRouter, Depends
from app.core.security import require_api_key

router = APIRouter()

@router.post("/complete")
async def complete(
    request: CompletionRequest,
    _: None = Depends(require_api_key)  # ← Dependency
):
    # Nếu đến đây → API key đã valid ✅
    # Xử lý request...
    return {"completion": "..."}
```

**Giải thích:**

### `Depends(require_api_key)`

**Flow:**
1. FastAPI nhận request POST /complete
2. Thấy dependency `Depends(require_api_key)`
3. Gọi `require_api_key()` **TRƯỚC** `complete()`
4. `require_api_key()`:
   - Extract Authorization header
   - Validate token
   - If valid → Return None (pass)
   - If invalid → Raise HTTPException (stop)
5. Nếu pass → Gọi `complete()`

---

### `_: None`

**Giải thích:**
- Variable name: `_` (convention cho "unused variable")
- Type: `None` (vì `require_api_key()` không return gì)
- Mục đích: Chỉ để trigger validation, không cần giá trị return

---

## 📊 Diagram: Authentication Flow

```
┌────────────────────────────────────────────────────────────┐
│                Client Request                               │
│  POST /complete                                            │
│  Authorization: Bearer 5conmeo                             │
│  Body: {"prefix": "...", "language": "python"}             │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────┐
│              FastAPI Dependency Injection                   │
│  Depends(require_api_key)                                  │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────┐
│              HTTPBearer extracts token                      │
│  Authorization: Bearer 5conmeo                             │
│  → scheme = "Bearer"                                       │
│  → credentials = "5conmeo"                                 │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────┐
│              require_api_key() validation                   │
│                                                            │
│  Check 1: settings.API_KEY empty?                          │
│    → Yes: Return (skip validation) ✅                      │
│    → No: Continue                                          │
│                                                            │
│  Check 2: credentials missing or scheme != "bearer"?       │
│    → Yes: Raise 401 Unauthorized ❌                        │
│    → No: Continue                                          │
│                                                            │
│  Check 3: credentials.credentials != settings.API_KEY?     │
│    → Yes: Raise 403 Forbidden ❌                           │
│    → No: Pass ✅                                           │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
                ┌────────┴────────┐
                │                 │
                ↓                 ↓
        ✅ Valid token      ❌ Invalid token
                │                 │
                │                 ↓
                │         HTTPException raised
                │                 │
                │                 ↓
                │         FastAPI returns error:
                │         401 or 403 response
                │
                ↓
        Continue to handler
        async def complete(...):
            # Process request
```

---

## 🧪 Test Cases

### Test 1: Valid token

```bash
curl -X POST http://localhost:9000/complete \
  -H "Authorization: Bearer 5conmeo" \
  -H "Content-Type: application/json" \
  -d '{"prefix": "def add(", "language": "python"}'

# Response: 200 OK
# {"completion": "a, b):\n    return a + b", ...}
```

---

### Test 2: Missing token

```bash
curl -X POST http://localhost:9000/complete \
  -H "Content-Type: application/json" \
  -d '{"prefix": "def add(", "language": "python"}'

# Response: 401 Unauthorized
# {"detail": "Missing Bearer token"}
```

---

### Test 3: Wrong scheme (Basic instead of Bearer)

```bash
curl -X POST http://localhost:9000/complete \
  -H "Authorization: Basic dXNlcjpwYXNz" \
  -H "Content-Type: application/json" \
  -d '{"prefix": "def add(", "language": "python"}'

# Response: 401 Unauthorized
# {"detail": "Missing Bearer token"}
```

---

### Test 4: Invalid token

```bash
curl -X POST http://localhost:9000/complete \
  -H "Authorization: Bearer wrong_token_123" \
  -H "Content-Type: application/json" \
  -d '{"prefix": "def add(", "language": "python"}'

# Response: 403 Forbidden
# {"detail": "Invalid token"}
```

---

### Test 5: Development mode (API_KEY empty)

```bash
# .env
API_KEY=

# Request without token:
curl -X POST http://localhost:9000/complete \
  -H "Content-Type: application/json" \
  -d '{"prefix": "def add(", "language": "python"}'

# Response: 200 OK (no auth required)
# {"completion": "..."}
```

---

## 💡 Những điểm quan trọng khi thuyết trình

### 1. Tại sao cần API key authentication?

**Without authentication:**
```
Anyone on internet → Backend → Groq API (using your API key)
                                 ↓
                         Your Groq credits depleted! 💸
```

**With authentication:**
```
Unknown user → Backend → 403 Forbidden ❌
Your extension → Backend (with valid key) → Groq API ✅
```

---

### 2. Bearer token là gì?

**Format:**
```
Authorization: Bearer <token>
```

**Bearer:** "Người mang token này có quyền truy cập"

**So với Basic Auth:**
```
# Basic: Username + Password (base64 encoded)
Authorization: Basic dXNlcjpwYXNz

# Bearer: Just a token (simpler, more modern)
Authorization: Bearer 5conmeo
```

---

### 3. Dependency Injection trong FastAPI

**Traditional approach:**
```python
@app.post("/complete")
async def complete(request):
    # Manual validation
    token = request.headers.get("Authorization")
    if not token or token != "Bearer 5conmeo":
        raise HTTPException(401)
    
    # Process...
```

**FastAPI approach (cleaner):**
```python
@app.post("/complete")
async def complete(
    request: CompletionRequest,
    _: None = Depends(require_api_key)  # Automatic validation
):
    # Nếu đến đây → Already valid!
    # Process...
```

**Benefits:**
- DRY (Don't Repeat Yourself)
- Testable (mock dependencies)
- Reusable (dùng cho nhiều endpoints)

---

### 4. 401 vs 403 status codes

| Code | Meaning | When to use |
|------|---------|-------------|
| 401 Unauthorized | "Bạn chưa đăng nhập" | Missing credentials, wrong scheme |
| 403 Forbidden | "Bạn không có quyền" | Wrong credentials, expired token |

**User-facing messages:**
```python
# 401: "Please provide API key in settings"
# 403: "Invalid API key. Check your configuration"
```

---

### 5. Security best practices

**✅ Good:**
```bash
# Store API key in .env (not committed)
API_KEY=super_secret_production_key_2024

# Use strong, random keys
API_KEY=$(openssl rand -base64 32)
```

**❌ Bad:**
```python
# Hardcoded in source code
API_KEY = "5conmeo"  # Don't do this in production!
```

**Production setup:**
```bash
# Render.com Environment Variables
API_KEY=<randomly generated 32-character string>

# Rotate key monthly
# Track which clients use which keys
```

---

## 🔐 Advanced: Multiple API Keys

**Current limitation:** Chỉ 1 API key cho tất cả clients

**Enhancement idea:**
```python
# config.py
VALID_API_KEYS = {
    "client_vscode_ext": "key_abc123",
    "client_jetbrains": "key_def456",
    "client_mobile_app": "key_ghi789"
}

# security.py
def require_api_key(credentials: ...):
    if credentials.credentials not in VALID_API_KEYS.values():
        raise HTTPException(403, "Invalid token")
    
    # Log which client made request
    client_name = get_client_name(credentials.credentials)
    logger.info(f"Request from {client_name}")
```

**Benefits:**
- Track usage per client
- Revoke specific keys without affecting others
- Rate limiting per client

---

## 📖 Reference: FastAPI Security Docs

**Official patterns:**

```python
# OAuth2 with Password (for user login)
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# API Key in query parameter
from fastapi.security import APIKeyQuery
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

# API Key in header
from fastapi.security import APIKeyHeader
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Our approach: Bearer token (most common for APIs)
from fastapi.security import HTTPBearer
security = HTTPBearer(auto_error=False)
```

---

**File này hoàn tất!** Tiếp theo: `postprocess.py` (xử lý output LLM). Tiếp tục không? 🔒
