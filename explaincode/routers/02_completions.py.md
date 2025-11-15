# Giải thích chi tiết: `server/app/routers/completions.py`

## 📋 Mục đích của file

File này implement **Main Completion Endpoints** - core functionality của AI Coder:
1. **`POST /complete`**: Synchronous completion
2. **`POST /complete_stream`**: Streaming completion (Server-Sent Events)
3. **Integrate** tất cả services: postprocess, formatter, telemetry, profiling
4. **Handle authentication** với API key
5. **User personalization** với style hints

---

## 🔍 Phân tích từng phần

### Import statements

```python
import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import StreamingResponse
from typing import Optional

from app.core.config import settings
from app.core.postprocess import postprocess
from app.core.formatter import format_code, should_format, normalize_python_code, normalize_cpp_code
from app.core.security import require_api_key
from app.middleware.telemetry import get_telemetry_collector
from app.schemas.completion import DEFAULT_STOPS_PY, DEFAULT_STOPS_CPP, CompleteRequest, CompleteResponse
from app.services.groq import build_prompt, call_groq_completion, new_request_id
from app.services.user_profiling import get_profiler
```

---

### Import Breakdown

**Standard library:**
- `json`: JSON serialization (cho streaming)
- `logging`: Logging completion requests
- `time`: Measure latency

**FastAPI:**
- `APIRouter`: Route grouping
- `Depends`: Dependency injection (authentication)
- `HTTPException`: Raise HTTP errors
- `Request`: Access request object
- `Header`: Extract HTTP headers
- `StreamingResponse`: Server-Sent Events

**Core services:**
- `settings`: Configuration
- `postprocess`: Clean LLM output
- `formatter`: Auto-format code
- `security`: API key authentication
- `telemetry`: Record usage data
- `CompleteRequest/CompleteResponse`: Request/response models
- `groq`: LLM API integration
- `user_profiling`: Personalization

---

## 🛠️ Router Setup

```python
router = APIRouter(prefix="", tags=["completion"])
logger = logging.getLogger("completion")
```

**Router config:**
- `prefix=""`: No prefix (root level)
- `tags=["completion"]`: OpenAPI grouping

**Logger:**
- Named logger: `"completion"`
- Separate from other components

---

## 🎯 Endpoint: POST `/complete`

### Purpose
**Main synchronous completion endpoint** - Return entire completion at once

### Function Signature

```python
@router.post("/complete", response_model=CompleteResponse, dependencies=[Depends(require_api_key)])
def complete(
    req: CompleteRequest,
    x_user_id: Optional[str] = Header(None, description="User identifier for personalization")
):
```

---

### Decorator Analysis

#### `@router.post("/complete", ...)`

**HTTP method:** `POST`
- Need request body (prefix, suffix, language)
- Not idempotent (each call may return different completion)

---

#### `response_model=CompleteResponse`

**Purpose:**
- FastAPI validates response against Pydantic model
- Auto-generates OpenAPI schema
- Type safety

**CompleteResponse schema:**
```python
class CompleteResponse(BaseModel):
    request_id: str
    completion: str
```

---

#### `dependencies=[Depends(require_api_key)]`

**Authentication:**
- Run `require_api_key()` before handler
- If no valid API key → 401 Unauthorized
- If valid → continue to handler

**Flow:**
```
Request
  ↓
require_api_key() ← Check Authorization header
  ↓ (if valid)
complete() ← Handler runs
  ↓
Response
```

**See:** `app.core.security.require_api_key()` (explained in 04_security.py.md)

---

### Parameters

#### `req: CompleteRequest`

**Pydantic model:**
```python
class CompleteRequest(BaseModel):
    prefix: str          # Code before cursor
    suffix: str          # Code after cursor
    language: str        # "python", "typescript", etc.
    max_tokens: int = 100
    temperature: float = 0.2
    stop: Optional[List[str]] = None
```

**Example:**
```json
{
  "prefix": "def add(a, b):\n    ",
  "suffix": "\n\nprint('test')",
  "language": "python",
  "max_tokens": 100,
  "temperature": 0.2
}
```

---

#### `x_user_id: Optional[str] = Header(None, ...)`

**Extract from HTTP header:**
```http
POST /complete
X-User-ID: user-123
Content-Type: application/json

{"prefix": "...", ...}
```

**Purpose:**
- User identification for personalization
- Track user-specific patterns
- Optional (can be `None`)

**Header() parameters:**
- `None`: Default value if header missing
- `description`: OpenAPI documentation

---

### Step 1: Initialize Request

```python
    req_id = new_request_id()
    start_time = time.time()
```

---

#### `new_request_id()`

**Generate unique request ID:**
```python
# From app.services.groq
def new_request_id() -> str:
    return str(uuid.uuid4())
```

**Example:**
```python
req_id = "550e8400-e29b-41d4-a716-446655440000"
```

**Purpose:**
- Track request through logs
- Correlate telemetry
- Return to client for debugging

---

#### `start_time = time.time()`

**Record timestamp:**
```python
start_time = 1699704225.123456  # Seconds since epoch
```

**Purpose:**
- Measure latency
- Record in telemetry
- Performance monitoring

---

### Step 2: Get User Style Hints

```python
    # Get personalized style hints if user_id provided
    user_style_hints = ""
    if x_user_id:
        try:
            profiler = get_profiler()
            user_style_hints = profiler.get_style_hints(x_user_id)
        except Exception as e:
            logger.warning(f"Failed to get style hints: {e}")
```

---

#### Check User ID

```python
    if x_user_id:
```

**Logic:**
- If header provided → get personalization
- If no header → skip (use default behavior)

---

#### Get Profiler Instance

```python
            profiler = get_profiler()
```

**Singleton pattern:**
```python
# From app.services.user_profiling
_profiler_instance: Optional[UserProfiler] = None

def get_profiler() -> UserProfiler:
    global _profiler_instance
    if _profiler_instance is None:
        _profiler_instance = UserProfiler()
    return _profiler_instance
```

---

#### Get Style Hints

```python
            user_style_hints = profiler.get_style_hints(x_user_id)
```

**Purpose:**
- Load user's coding style preferences
- Example: `"Use type hints. Prefer list comprehensions."`
- Inject into prompt for personalized completions

**Example hints:**
```python
user_style_hints = """
Based on your history:
- Use type hints (e.g., def func(x: int) -> str)
- Prefer list comprehensions over loops
- Add docstrings to functions
"""
```

---

#### Error Handling

```python
        except Exception as e:
            logger.warning(f"Failed to get style hints: {e}")
```

**Fail gracefully:**
- If profiling fails → continue without personalization
- Don't crash request
- Log warning for debugging

---

### Step 3: Build Prompt

```python
    prompt = build_prompt(req, user_style_hints)
```

**Purpose:**
- Construct FIM (Fill-In-the-Middle) prompt
- Include user style hints
- Format for Groq API

**See:** `app.services.groq.build_prompt()` (detailed in services/groq.py)

**Example prompt:**
```
<｜fim▁begin｜>def add(a, b):
    <｜fim▁hole｜>

print('test')<｜fim▁end｜>

User style: Use type hints.
```

---

### Step 4: Choose Stop Sequences

```python
    # Choose appropriate stop sequences based on language
    default_stops = DEFAULT_STOPS_CPP if req.language in ["cpp", "c++", "c"] else DEFAULT_STOPS_PY
    stops = (req.stop or []) + default_stops
```

---

#### Language-Specific Stops

```python
    default_stops = DEFAULT_STOPS_CPP if req.language in ["cpp", "c++", "c"] else DEFAULT_STOPS_PY
```

**From schemas/completion.py:**
```python
DEFAULT_STOPS_PY = [
    "\ndef ", "\nclass ", "\nif ", "\n#", "```"
]

DEFAULT_STOPS_CPP = [
    "\nvoid ", "\nint ", "\nclass ", "\n//", "```"
]
```

**Purpose:**
- Stop generation at logical boundaries
- Prevent incomplete code blocks
- Language-specific patterns

---

#### Combine Stops

```python
    stops = (req.stop or []) + default_stops
```

**Logic:**
```python
# User provided custom stops:
req.stop = ["\nTODO", "\nFIXME"]

# Combine with defaults:
stops = ["\nTODO", "\nFIXME"] + ["\ndef ", "\nclass ", ...]
# → ["\nTODO", "\nFIXME", "\ndef ", "\nclass ", ...]
```

**`req.stop or []`:**
- If `req.stop = None` → use `[]`
- If `req.stop = [...]` → use that list

---

### Step 5: Call Groq & Process

```python
    try:
        raw = call_groq_completion(prompt, req.max_tokens, req.temperature, stops)
        completion = (
            postprocess(req.prefix, req.suffix, raw, stops) if settings.POSTPROCESS_ENABLED else raw
        )
```

---

#### Call Groq API

```python
        raw = call_groq_completion(prompt, req.max_tokens, req.temperature, stops)
```

**Function from `app.services.groq`:**
- Send prompt to Groq API
- Get raw completion text
- Handle errors (timeouts, rate limits)

**Example:**
```python
# Input:
prompt = "<｜fim▁begin｜>def add(a, b):\n    <｜fim▁hole｜>..."
max_tokens = 100
temperature = 0.2
stops = ["\ndef ", "\nclass "]

# Output:
raw = "return a + b\n\ndef "
```

---

#### Postprocess (Optional)

```python
        completion = (
            postprocess(req.prefix, req.suffix, raw, stops) if settings.POSTPROCESS_ENABLED else raw
        )
```

**Conditional postprocessing:**
- If `POSTPROCESS_ENABLED=true` → clean output
- If disabled → use raw output

**Postprocess steps:**
- Strip markdown fences (` ``` `)
- Cut at stop sequences
- Remove duplicates
- Align indentation

**See:** `app.core.postprocess` (explained in 05_postprocess.py.md)

**Example:**
```python
# Before:
raw = "```python\nreturn a + b\n```\ndef "

# After postprocess:
completion = "return a + b"
```

---

### Step 6: Auto-Format

```python
        # Auto-format if enabled and applicable
        if settings.AUTO_FORMAT and should_format(completion, req.language):
            formatted, error = format_code(completion, req.language)
            if error:
                logger.warning(f"Format failed: {error}, using normalization fallback")
                if req.language == "python":
                    completion = normalize_python_code(completion)
                elif req.language in ["cpp", "c++", "c"]:
                    completion = normalize_cpp_code(completion)
            else:
                completion = formatted
        else:
            # If auto-format is disabled, still apply lightweight normalization
            if req.language == "python":
                completion = normalize_python_code(completion)
            elif req.language in ["cpp", "c++", "c"]:
                completion = normalize_cpp_code(completion)
```

---

#### Check if Should Format

```python
        if settings.AUTO_FORMAT and should_format(completion, req.language):
```

**Two conditions:**
1. `AUTO_FORMAT=true` (from config)
2. `should_format()` returns `True` (heuristics)

**should_format() logic:**
```python
# From app.core.formatter
def should_format(code: str, language: str) -> bool:
    # Too short → skip
    if len(code.strip()) < 10:
        return False
    
    # Has basic structure (def, class, etc.)
    if language == "python":
        return any(kw in code for kw in ["def ", "class ", "if ", "for "])
    
    return True
```

---

#### Try Formatting

```python
            formatted, error = format_code(completion, req.language)
```

**Returns tuple:**
- `formatted`: Formatted code (or original if error)
- `error`: Error message (or `None`)

**Example success:**
```python
# Input:
completion = "def add(a,b):\nreturn a+b"

# Output:
formatted = "def add(a, b):\n    return a + b"
error = None
```

**Example failure:**
```python
# Input (syntax error):
completion = "def add(a, b):\n    return"

# Output:
formatted = "def add(a, b):\n    return"  # Unchanged
error = "black formatting failed: invalid syntax"
```

---

#### Handle Format Error

```python
            if error:
                logger.warning(f"Format failed: {error}, using normalization fallback")
                if req.language == "python":
                    completion = normalize_python_code(completion)
                elif req.language in ["cpp", "c++", "c"]:
                    completion = normalize_cpp_code(completion)
            else:
                completion = formatted
```

**Fallback strategy:**
1. Try `black` formatter (Python) or `clang-format` (C++)
2. If fails → use lightweight normalization
3. Normalization = simple regex-based cleanup (safe, always works)

**normalize_python_code():**
```python
# From app.core.formatter
def normalize_python_code(code: str) -> str:
    # Fix spacing around operators
    code = re.sub(r'([+\-*/%])([^ ])', r'\1 \2', code)
    # Fix indentation (basic)
    # Remove trailing whitespace
    return code
```

---

#### Normalization Fallback (No Auto-Format)

```python
        else:
            # If auto-format is disabled, still apply lightweight normalization
            if req.language == "python":
                completion = normalize_python_code(completion)
            elif req.language in ["cpp", "c++", "c"]:
                completion = normalize_cpp_code(completion)
```

**Why normalize even if AUTO_FORMAT disabled?**
- LLM output can be messy
- Basic cleanup always helpful
- Normalization is safe (no subprocess, fast)

---

### Step 7: Record Telemetry

```python
        # Record telemetry
        latency_ms = (time.time() - start_time) * 1000
        try:
            telemetry = get_telemetry_collector()
            telemetry.record_completion(
                request_id=req_id,
                prefix=req.prefix,
                suffix=req.suffix,
                language=req.language,
                completion=completion,
                latency_ms=latency_ms,
                model=settings.GROQ_MODEL,
                user_id=x_user_id  # Include user_id in telemetry
            )
        except Exception as e:
            logger.error(f"Telemetry recording failed: {e}")
```

---

#### Calculate Latency

```python
        latency_ms = (time.time() - start_time) * 1000
```

**Calculation:**
```python
# Start time (set earlier):
start_time = 1699704225.123456

# Current time:
time.time() = 1699704225.456789

# Difference (seconds):
time.time() - start_time = 0.333333

# Convert to milliseconds:
latency_ms = 0.333333 * 1000 = 333.33 ms
```

---

#### Record Completion Event

```python
            telemetry.record_completion(
                request_id=req_id,
                prefix=req.prefix,
                suffix=req.suffix,
                language=req.language,
                completion=completion,
                latency_ms=latency_ms,
                model=settings.GROQ_MODEL,
                user_id=x_user_id
            )
```

**Purpose:**
- Log to daily JSONL file
- Track usage patterns
- Generate statistics
- Export training data

**See:** `app.middleware.telemetry` (explained in 02_telemetry.py.md)

---

#### Fail Gracefully

```python
        except Exception as e:
            logger.error(f"Telemetry recording failed: {e}")
```

**Don't crash request:**
- Telemetry is non-critical
- Request should succeed even if telemetry fails
- Log error for debugging

---

### Step 8: Return Response

```python
        return {"request_id": req_id, "completion": completion}
```

**Response schema (CompleteResponse):**
```python
{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "completion": "return a + b"
}
```

**Client receives:**
- Request ID for debugging/correlation
- Completion text to insert

---

### Error Handling

```python
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unknown error: {e}") from e
```

---

#### Re-raise HTTPException

```python
    except HTTPException:
        raise
```

**Purpose:**
- HTTPException from `call_groq_completion()` or other services
- Already formatted correctly (status code, detail)
- Pass through unchanged

**Example:**
```python
# In call_groq_completion():
if resp.status_code == 429:
    raise HTTPException(status_code=429, detail="Rate limit exceeded")

# In complete():
except HTTPException:  # Catch it
    raise  # Re-raise as-is (don't wrap)
```

---

#### Catch Unknown Errors

```python
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unknown error: {e}") from e
```

**Safety net:**
- Unexpected errors (not HTTPException)
- Convert to 500 Internal Server Error
- Include error message in detail

**Example:**
```python
# Unexpected error:
KeyError: 'some_key'

# Converted to:
HTTPException(status_code=500, detail="Unknown error: 'some_key'")
```

---

## 🌊 Endpoint: POST `/complete_stream`

### Purpose
**Streaming completion endpoint** - Return completion incrementally via Server-Sent Events (SSE)

### Function Signature

```python
@router.post("/complete_stream", dependencies=[Depends(require_api_key)])
def complete_stream(
    req: CompleteRequest,
    request: Request,
    x_user_id: Optional[str] = Header(None, description="User identifier for personalization")
):
    """
    Streaming endpoint - NOTE: Groq API returns full response, we simulate streaming.
    For true streaming, consider using Groq's streaming API in future.
    """
```

---

### Differences from `/complete`

**No `response_model`:**
- Streaming response (not single JSON object)
- SSE format (text/event-stream)

**Additional parameter:**
```python
    request: Request,
```

**Purpose:**
- Access `request.state.request_id` (from middleware)
- Log with request correlation

---

### Initialize

```python
    req_id = new_request_id()
    
    # Get personalized style hints if user_id provided
    user_style_hints = ""
    if x_user_id:
        try:
            profiler = get_profiler()
            user_style_hints = profiler.get_style_hints(x_user_id)
        except Exception as e:
            logger.warning(f"Failed to get style hints: {e}")
    
    prompt = build_prompt(req, user_style_hints)
    
    # Choose appropriate stop sequences based on language
    default_stops = DEFAULT_STOPS_CPP if req.language in ["cpp", "c++", "c"] else DEFAULT_STOPS_PY
    stops = (req.stop or []) + default_stops
```

**Same as `/complete`:**
- Generate request ID
- Get user hints
- Build prompt
- Choose stops

---

### Generator Function

```python
    def gen():
        yield f"event: meta\ndata: {json.dumps({'request_id': req_id})}\n\n"
```

---

#### Server-Sent Events (SSE) Format

**Structure:**
```
event: <event_type>
data: <json_data>

```

**Rules:**
- Each message ends with `\n\n` (two newlines)
- `event:` optional (default: `message`)
- `data:` required (payload)

**Example:**
```
event: meta
data: {"request_id": "abc-123"}

event: chunk
data: {"delta": "return "}

event: chunk
data: {"delta": "a + b"}

event: done
data: {}

```

---

#### First Event: Meta

```python
        yield f"event: meta\ndata: {json.dumps({'request_id': req_id})}\n\n"
```

**Output:**
```
event: meta
data: {"request_id": "550e8400-e29b-41d4-a716-446655440000"}

```

**Purpose:**
- Send request ID immediately
- Client can display loading state with ID
- Useful for debugging

---

### Try Block: Generate Completion

```python
        try:
            # Groq returns full completion (not streaming yet)
            raw = call_groq_completion(prompt, req.max_tokens, req.temperature, stops)
```

**Note in docstring:**
```
NOTE: Groq API returns full response, we simulate streaming.
```

**Current implementation:**
- Call Groq (blocks until complete)
- Then chunk and stream to client
- Future: Use Groq streaming API for true streaming

---

### Simulate Streaming (Chunking)

```python
            # Simulate streaming by chunking
            chunk_size = 10
            for i in range(0, len(raw), chunk_size):
                chunk = raw[i:i+chunk_size]
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
```

---

#### Chunking Logic

```python
            chunk_size = 10
            for i in range(0, len(raw), chunk_size):
                chunk = raw[i:i+chunk_size]
```

**Example:**
```python
raw = "return a + b"  # Length: 12
chunk_size = 10

# Loop:
i = 0:  chunk = raw[0:10] = "return a +"
i = 10: chunk = raw[10:12] = " b"

# Chunks: ["return a +", " b"]
```

---

#### Yield Chunks

```python
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
```

**Output:**
```
data: {"delta": "return a +"}

data: {"delta": " b"}

```

**Client receives:**
- First chunk → display "return a +"
- Second chunk → append " b" → display "return a + b"
- Progressive rendering (typewriter effect)

---

### Postprocess Complete Result

```python
            final = (
                postprocess(req.prefix, req.suffix, raw, stops) if settings.POSTPROCESS_ENABLED else raw
            )

            # Apply same formatting/normalization logic as non-streaming endpoint
            if settings.AUTO_FORMAT and should_format(final, req.language):
                formatted, error = format_code(final, req.language)
                if error:
                    logger.warning(f"Format failed in stream: {error}, using normalization fallback")
                    if req.language == "python":
                        final = normalize_python_code(final)
                    elif req.language in ["cpp", "c++", "c"]:
                        final = normalize_cpp_code(final)
                else:
                    final = formatted
            else:
                if req.language == "python":
                    final = normalize_python_code(final)
                elif req.language in ["cpp", "c++", "c"]:
                    final = normalize_cpp_code(final)
```

**Same processing as `/complete`:**
- Postprocess (clean)
- Auto-format (if enabled)
- Normalize (fallback)

---

### Send Final Event

```python
            yield f"event: final\ndata: {json.dumps({'completion': final})}\n\n"
            yield "event: done\ndata: {}\n\n"
```

---

#### Final Event

```python
            yield f"event: final\ndata: {json.dumps({'completion': final})}\n\n"
```

**Output:**
```
event: final
data: {"completion": "return a + b"}

```

**Purpose:**
- Send cleaned/formatted completion
- Client can replace raw chunks with final version

---

#### Done Event

```python
            yield "event: done\ndata: {}\n\n"
```

**Output:**
```
event: done
data: {}

```

**Purpose:**
- Signal completion
- Client closes connection
- No more data coming

---

### Error Handling in Generator

```python
        except Exception as e:
            logger.exception("Error in streaming completion")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
```

**Error event:**
```
event: error
data: {"error": "Timeout: 30s exceeded"}

```

**Client handling:**
```typescript
eventSource.addEventListener('error', (e) => {
    const data = JSON.parse(e.data);
    console.error('Completion error:', data.error);
    // Show error message to user
});
```

---

### Return StreamingResponse

```python
    rid = getattr(request.state, settings.REQUEST_ID, "-")
    logger.info("Received /complete_stream", extra={settings.REQUEST_ID: rid})
    return StreamingResponse(gen(), media_type="text/event-stream")
```

---

#### Get Request ID from Middleware

```python
    rid = getattr(request.state, settings.REQUEST_ID, "-")
```

**Purpose:**
- `request.state.request_id` set by `request_id_middleware`
- Use for logging correlation

**See:** `app.middleware.request_id` (explained in 01_request_id.py.md)

---

#### Log Request

```python
    logger.info("Received /complete_stream", extra={settings.REQUEST_ID: rid})
```

**Output:**
```
[INFO] [abc-123] Received /complete_stream
```

**Correlation:**
- All logs for this request have same `[abc-123]`
- Easy to trace through logs

---

#### StreamingResponse

```python
    return StreamingResponse(gen(), media_type="text/event-stream")
```

**Parameters:**

**`gen()`:**
- Generator function
- FastAPI calls repeatedly
- Each `yield` → send to client

**`media_type="text/event-stream"`:**
- Content-Type header
- Required for SSE
- Client knows how to parse

**Response headers:**
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

---

## 📊 Diagram: Complete Request Flow

```
┌─────────────────────────────────────────────────────┐
│                Client Request                        │
│  POST /complete                                     │
│  Authorization: Bearer sk_abc123...                 │
│  X-User-ID: user-456                                │
│  {                                                  │
│    "prefix": "def add(a, b):\n    ",               │
│    "suffix": "\n\nprint('test')",                  │
│    "language": "python",                            │
│    "max_tokens": 100,                               │
│    "temperature": 0.2                               │
│  }                                                  │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│        require_api_key (Dependency)                  │
│  Check Authorization header                          │
│  → Valid: Continue                                  │
│  → Invalid: 401 Unauthorized                        │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│              complete() Handler                      │
│                                                     │
│  1. Generate request_id                             │
│     req_id = new_request_id()                       │
│     → "550e8400-e29b-41d4-a716-446655440000"       │
│                                                     │
│  2. Start timer                                     │
│     start_time = time.time()                        │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│         Get User Personalization                     │
│  if x_user_id:                                      │
│      profiler.get_style_hints(x_user_id)           │
│      → "Use type hints. Prefer comprehensions."     │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│              Build Prompt                            │
│  prompt = build_prompt(req, user_style_hints)       │
│  → FIM format with context:                         │
│     <｜fim▁begin｜>def add(a, b):                    │
│         <｜fim▁hole｜>                               │
│     print('test')<｜fim▁end｜>                      │
│     User style: Use type hints.                     │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│         Choose Stop Sequences                        │
│  default_stops = DEFAULT_STOPS_PY                   │
│  stops = req.stop + default_stops                   │
│  → ["\ndef ", "\nclass ", "\nif ", "\n#", "```"]   │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│            Call Groq API                             │
│  raw = call_groq_completion(prompt, ...)            │
│  → "return a + b\n\ndef "                           │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│            Postprocess Output                        │
│  if POSTPROCESS_ENABLED:                            │
│      completion = postprocess(...)                  │
│      → "return a + b"  (cleaned)                    │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│         Auto-Format / Normalize                      │
│  if AUTO_FORMAT and should_format():                │
│      formatted, error = format_code(...)            │
│      if not error:                                  │
│          completion = formatted                     │
│      else:                                          │
│          completion = normalize_python_code(...)    │
│  → "return a + b"  (formatted)                      │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│            Record Telemetry                          │
│  latency_ms = (time.time() - start_time) * 1000    │
│  telemetry.record_completion(                       │
│      request_id=req_id,                             │
│      prefix=req.prefix,                             │
│      completion=completion,                         │
│      latency_ms=234.56,                             │
│      ...                                            │
│  )                                                  │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│               Return Response                        │
│  {                                                  │
│    "request_id": "550e8400-...",                    │
│    "completion": "return a + b"                     │
│  }                                                  │
└─────────────────────────────────────────────────────┘
```

---

## 📊 Diagram: Streaming Flow

```
┌─────────────────────────────────────────────────────┐
│           Client Opens SSE Connection                │
│  POST /complete_stream                              │
│  (Same request body as /complete)                   │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│        complete_stream() → gen() Generator           │
│                                                     │
│  Event 1 - Meta:                                    │
│  ┌───────────────────────────────────────┐         │
│  │ event: meta                            │         │
│  │ data: {"request_id": "550e8400-..."}  │         │
│  │                                        │         │
│  └───────────────────────────────────────┘         │
│                     ↓ Client receives immediately  │
└─────────────────────────────────────────────────────┘
                     │
                     ↓ Call Groq (blocks)
┌─────────────────────────────────────────────────────┐
│         Groq API Returns (after 200ms)               │
│  raw = "return a + b"                               │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓ Chunk into 10-char pieces
┌─────────────────────────────────────────────────────┐
│          Stream Chunks to Client                     │
│                                                     │
│  Event 2 - Chunk 1:                                 │
│  ┌───────────────────────────────────────┐         │
│  │ data: {"delta": "return a +"}         │         │
│  │                                        │         │
│  └───────────────────────────────────────┘         │
│                     ↓ Client renders                │
│                                                     │
│  Event 3 - Chunk 2:                                 │
│  ┌───────────────────────────────────────┐         │
│  │ data: {"delta": " b"}                 │         │
│  │                                        │         │
│  └───────────────────────────────────────┘         │
│                     ↓ Client appends                │
└─────────────────────────────────────────────────────┘
                     │
                     ↓ Postprocess + Format
┌─────────────────────────────────────────────────────┐
│           Send Final Cleaned Version                 │
│                                                     │
│  Event 4 - Final:                                   │
│  ┌───────────────────────────────────────┐         │
│  │ event: final                           │         │
│  │ data: {"completion": "return a + b"}  │         │
│  │                                        │         │
│  └───────────────────────────────────────┘         │
│                     ↓ Client replaces chunks        │
│                                                     │
│  Event 5 - Done:                                    │
│  ┌───────────────────────────────────────┐         │
│  │ event: done                            │         │
│  │ data: {}                               │         │
│  │                                        │         │
│  └───────────────────────────────────────┘         │
│                     ↓ Client closes connection      │
└─────────────────────────────────────────────────────┘
```

---

## 💡 Key Points cho thuyết trình

### 1. Synchronous vs Streaming

**Comparison:**

| Aspect | `/complete` | `/complete_stream` |
|--------|-------------|-------------------|
| **Response** | Single JSON | Server-Sent Events |
| **UX** | Wait → Full result | Progressive (typewriter) |
| **Complexity** | Simple | More complex |
| **Use case** | Quick completions | Long completions |

---

### 2. Pipeline Architecture

**Processing stages:**
```
Input → Auth → Personalization → Prompt Building
  ↓
Groq API → Postprocess → Format → Telemetry
  ↓
Output
```

**Each stage is modular:**
- Can enable/disable postprocess
- Can enable/disable auto-format
- Can enable/disable telemetry
- Easy to test independently

---

### 3. Error Handling Strategy

**Graceful degradation:**
```python
# Personalization fails → continue without hints
try:
    user_style_hints = profiler.get_style_hints(x_user_id)
except:
    user_style_hints = ""  # Default

# Format fails → use normalization
if format_error:
    completion = normalize_python_code(completion)

# Telemetry fails → log but don't crash
try:
    telemetry.record_completion(...)
except:
    logger.error("Telemetry failed")
# Request still succeeds!
```

---

### 4. Personalization

**User-specific completions:**
```python
# User A (uses type hints):
user_style_hints = "Use type hints"
# Completion: def add(a: int, b: int) -> int:

# User B (no type hints):
user_style_hints = ""
# Completion: def add(a, b):
```

**Benefits:**
- Better user experience
- Matches coding style
- Learns over time

---

### 5. Stop Sequences

**Why important?**
```python
# Without stops:
raw = "return a + b\n\ndef subtract(a, b):\n    return a - b\n\n"
# → Too much! Includes unrelated code

# With stops ["\ndef "]:
raw = "return a + b\n\ndef "
# After postprocess:
completion = "return a + b"
# → Perfect! Just the function body
```

---

### 6. Telemetry Integration

**Non-intrusive:**
- Record after completion (not blocking)
- Fails gracefully
- Provides valuable insights

**Data collected:**
- Request ID (correlation)
- Latency (performance)
- Language distribution
- User patterns

---

### 7. Server-Sent Events (SSE)

**Why SSE?**
- Simple (just HTTP)
- One-way (server → client)
- Auto-reconnect
- Text-based (easy to debug)

**Alternative: WebSockets**
```
SSE:
+ Simpler
+ HTTP-compatible (no firewall issues)
+ Auto-reconnect
- One-way only

WebSockets:
+ Two-way communication
+ Binary support
- More complex
- Firewall issues
```

---

## 🧪 Test Cases

### Test 1: Basic completion

```python
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch

client = TestClient(app)

# Mock Groq API
with patch('app.services.groq.call_groq_completion', return_value="return a + b"):
    response = client.post(
        "/complete",
        headers={"Authorization": "Bearer test-key"},
        json={
            "prefix": "def add(a, b):\n    ",
            "suffix": "",
            "language": "python",
            "max_tokens": 100,
            "temperature": 0.2
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert "completion" in data
    assert data["completion"] == "return a + b"
```

---

### Test 2: Unauthorized (no API key)

```python
response = client.post(
    "/complete",
    json={"prefix": "def add(", "language": "python"}
)

assert response.status_code == 401
assert "not authenticated" in response.json()["detail"].lower()
```

---

### Test 3: With user personalization

```python
with patch('app.services.groq.call_groq_completion', return_value="return a + b"):
    with patch('app.services.user_profiling.get_profiler') as mock_profiler:
        mock_profiler.return_value.get_style_hints.return_value = "Use type hints"
        
        response = client.post(
            "/complete",
            headers={
                "Authorization": "Bearer test-key",
                "X-User-ID": "user-123"
            },
            json={
                "prefix": "def add(a, b):\n    ",
                "language": "python"
            }
        )
        
        assert response.status_code == 200
        # Verify style hints were used
        mock_profiler.return_value.get_style_hints.assert_called_with("user-123")
```

---

### Test 4: Streaming endpoint

```python
with patch('app.services.groq.call_groq_completion', return_value="return a + b"):
    response = client.post(
        "/complete_stream",
        headers={"Authorization": "Bearer test-key"},
        json={"prefix": "def add(", "language": "python"}
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"
    
    # Parse SSE events
    content = response.text
    assert "event: meta" in content
    assert "event: final" in content
    assert "event: done" in content
```

---

### Test 5: Error handling (Groq API failure)

```python
from fastapi import HTTPException

with patch('app.services.groq.call_groq_completion', side_effect=HTTPException(status_code=429, detail="Rate limit")):
    response = client.post(
        "/complete",
        headers={"Authorization": "Bearer test-key"},
        json={"prefix": "def add(", "language": "python"}
    )
    
    assert response.status_code == 429
    assert "Rate limit" in response.json()["detail"]
```

---

## 🔧 Usage Example (Client Side)

### Synchronous Completion

```typescript
// TypeScript client
async function getCompletion(prefix: string, suffix: string) {
    const response = await fetch('http://localhost:8000/complete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer sk_abc123...',
            'X-User-ID': 'user-456'
        },
        body: JSON.stringify({
            prefix: prefix,
            suffix: suffix,
            language: 'python',
            max_tokens: 100,
            temperature: 0.2
        })
    });
    
    const data = await response.json();
    console.log('Request ID:', data.request_id);
    return data.completion;
}

// Usage:
const completion = await getCompletion("def add(a, b):\n    ", "");
console.log(completion);  // "return a + b"
```

---

### Streaming Completion

```typescript
async function getCompletionStream(prefix: string, suffix: string) {
    const eventSource = new EventSource('http://localhost:8000/complete_stream', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer sk_abc123...'
        },
        body: JSON.stringify({
            prefix: prefix,
            suffix: suffix,
            language: 'python'
        })
    });
    
    let completion = '';
    
    eventSource.addEventListener('meta', (e) => {
        const data = JSON.parse(e.data);
        console.log('Request ID:', data.request_id);
    });
    
    eventSource.addEventListener('message', (e) => {
        const data = JSON.parse(e.data);
        if (data.delta) {
            completion += data.delta;
            // Update UI with partial completion
            updateEditor(completion);
        }
    });
    
    eventSource.addEventListener('final', (e) => {
        const data = JSON.parse(e.data);
        completion = data.completion;  // Replace with cleaned version
        updateEditor(completion);
    });
    
    eventSource.addEventListener('done', (e) => {
        eventSource.close();
        console.log('Stream complete:', completion);
    });
    
    eventSource.addEventListener('error', (e) => {
        const data = JSON.parse(e.data);
        console.error('Error:', data.error);
        eventSource.close();
    });
}
```

---

**File này hoàn tất!** 🎉 Đây là file phức tạp nhất trong routers/. 

**Tiếp theo:** `services/` directory (groq.py, user_profiling.py). Tiếp tục không? 🚀

