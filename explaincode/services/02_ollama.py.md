# Giải thích chi tiết: `server/app/services/ollama.py`

## 📋 Mục đích của file

File này implement **Ollama Integration** - alternative LLM provider:
1. **Local LLM support** (chạy model trên máy local)
2. **Ollama Cloud support** (API key authentication)
3. **Build prompts** với few-shot examples
4. **Call Ollama API** (/api/generate endpoint)
5. **Error handling** (network, API errors)
6. **Backward compatibility** (legacy service)

**Ollama = Alternative to Groq** (local/self-hosted option)

---

## 🔍 Phân tích từng phần

### Import statements

```python
import uuid

from fastapi import HTTPException
import logging

from app.core.config import settings
from app.core.http import SESSION, TIMEOUT
from app.schemas.completion import CompleteRequest

logger = logging.getLogger(__name__)
```

**Giải thích:**

- `uuid`: Generate request IDs
- `HTTPException`: Raise HTTP errors
- `logging`: Log API calls and errors
- `settings`: Config (model name, Ollama URL, API key)
- `SESSION, TIMEOUT`: Shared HTTP client from core.http
- `CompleteRequest`: Request schema
- `logger`: Module-level logger

---

## 🎯 Function: `build_prompt()`

### Purpose
**Xây dựng prompt** cho Ollama API - ĐƠN GIẢN HƠN Groq!

### Function Signature

```python
def build_prompt(seq: CompleteRequest) -> str:
    """
    Build an enhanced prompt with clear instructions and few-shot examples.
    Emphasizes returning ONLY raw code without markdown formatting.
    """
```

**Note:** Parameter name là `seq` (sequence) thay vì `req` (request)

---

### Step 1: Define Rules

```python
    rules = [
        f"Return ONLY the missing {seq.language} code that should appear at the cursor position.",
        "CRITICAL: Never use markdown code blocks, backticks (```), or any formatting markers.",
        "Output must be pure, executable code that can be inserted directly into the file.",
        "Do not add explanations, comments, or docstrings unless they are part of the actual code logic.",
        "Respect the exact indentation from the last line before the cursor.",
        "Do not repeat any code that already exists in the prefix or suffix.",
        "If the prefix ends with ':', indent the completion by 4 spaces (Python block).",
        "Keep completions concise but complete - finish the current logical block.",
    ]
```

---

### Phân tích Rules (8 quy tắc)

#### Rule 1: Code only at cursor

```python
f"Return ONLY the missing {seq.language} code that should appear at the cursor position."
```

**Example:**
```python
seq.language = "python"
# → "Return ONLY the missing python code that should appear at the cursor position."
```

**Purpose:** Clear task definition

---

#### Rule 2: No markdown formatting

```python
"CRITICAL: Never use markdown code blocks, backticks (```), or any formatting markers."
```

**Problem it solves:**

**Bad LLM output:**
```
```python
def add(a, b):
    return a + b
```
```

**Good LLM output:**
```python
def add(a, b):
    return a + b
```

**No ``` markers!**

---

#### Rule 3: Executable code

```python
"Output must be pure, executable code that can be inserted directly into the file."
```

**Requirement:**
- Can paste directly into editor
- No preprocessing needed
- Syntactically correct

---

#### Rule 4: No extra explanations

```python
"Do not add explanations, comments, or docstrings unless they are part of the actual code logic."
```

**Bad (with explanation):**
```python
# This function calculates the sum of two numbers
def add(a, b):
    return a + b  # Return the sum
```

**Good (clean):**
```python
def add(a, b):
    return a + b
```

**Comments OK only if part of actual logic!**

---

#### Rule 5: Respect indentation

```python
"Respect the exact indentation from the last line before the cursor."
```

**Example:**

**PREFIX:**
```python
class MyClass:
    def method(self):
        if condition:
            ← Cursor here (12 spaces indent)
```

**Completion must have 12 spaces:**
```python
            return True  ← 12 spaces
```

---

#### Rule 6: Don't repeat code

```python
"Do not repeat any code that already exists in the prefix or suffix."
```

**PREFIX:**
```python
def add(a, b):
    ← Cursor
```

**Bad (repeats):**
```python
def add(a, b):  ← Already in PREFIX!
    return a + b
```

**Good:**
```python
    return a + b  ← Only missing part
```

---

#### Rule 7: Python block indentation

```python
"If the prefix ends with ':', indent the completion by 4 spaces (Python block)."
```

**Python-specific rule:**

**PREFIX ends with `:`:**
```python
def foo():
    ← Colon above, so indent 4 spaces
```

**Completion:**
```python
    pass  ← 4 spaces added
```

**Works for:**
- `def foo():`
- `if condition:`
- `for item in items:`
- `class MyClass:`
- `with open(...) as f:`

---

#### Rule 8: Concise but complete

```python
"Keep completions concise but complete - finish the current logical block."
```

**Balance:**
- **Concise**: Don't generate entire file
- **Complete**: Finish current statement/block

**Example:**

**PREFIX:**
```python
def calculate_total(items):
    ← Cursor
```

**Good (completes function):**
```python
    total = 0
    for item in items:
        total += item.price
    return total
```

**Bad (too much - generates next function):**
```python
    total = 0
    for item in items:
        total += item.price
    return total

def calculate_average(items):  ← Stop! This is a new function
    ...
```

---

### Step 2: Few-Shot Examples

```python
    # Few-shot examples to guide the model
    examples = f"""
EXAMPLE 1 - Function body completion:
<prefix>
def add(a, b):
    
</prefix>
<suffix>

def multiply(x, y):
</suffix>
CORRECT OUTPUT:
    return a + b

EXAMPLE 2 - Continue statement:
<prefix>
if user.is_authenticated:
    
</prefix>
<suffix>
else:
    return redirect('/login')
</suffix>
CORRECT OUTPUT:
    return render_template('dashboard.html')

EXAMPLE 3 - List comprehension:
<prefix>
numbers = [1, 2, 3, 4, 5]
squares = [
</prefix>
<suffix>
]
print(squares)
</suffix>
CORRECT OUTPUT:
x**2 for x in numbers

---
"""
```

---

### Phân tích Few-Shot Examples

#### Example 1: Function body

**Structure:**
```
<prefix> ... </prefix>  ← Before cursor
<suffix> ... </suffix>  ← After cursor
CORRECT OUTPUT: ...     ← Expected completion
```

**Teaching:**
```python
<prefix>
def add(a, b):
    ← Empty function body
</prefix>
<suffix>

def multiply(x, y):  ← Next function
</suffix>
CORRECT OUTPUT:
    return a + b  ← Simple, direct
```

**LLM learns:**
- 4 spaces indentation (Python block after `:`)
- Simple return statement
- Don't continue to next function

---

#### Example 2: If-statement

```python
<prefix>
if user.is_authenticated:
    ← Cursor inside if block
</prefix>
<suffix>
else:  ← Else block comes after
    return redirect('/login')
</suffix>
CORRECT OUTPUT:
    return render_template('dashboard.html')
```

**Teaching:**
- Complete if branch
- Context-aware (knows else block exists)
- Match indentation (4 spaces)
- Stop before else

---

#### Example 3: List comprehension

```python
<prefix>
numbers = [1, 2, 3, 4, 5]
squares = [  ← List starts here
</prefix>
<suffix>
]  ← List closes here
print(squares)
</suffix>
CORRECT OUTPUT:
x**2 for x in numbers  ← Just the comprehension part
```

**Teaching:**
- Inline completion (no indentation)
- List comprehension syntax
- Don't include `[` or `]` (already in prefix/suffix)

---

### Step 3: Build Final Prompt

```python
    return (
        f"You are an expert {seq.language} code completion AI assistant.\n"
        "Your ONLY job is to complete the code at the cursor position.\n\n"
        "RULES (follow ALL strictly):\n- " + "\n- ".join(rules) + "\n\n"
        + examples +
        "NOW complete the following code at <cursor/> position:\n\n"
        f"<prefix>\n{seq.prefix}\n</prefix>\n\n"
        f"<suffix>\n{seq.suffix}\n</suffix>\n\n"
        "<cursor/>\n\n"
        "OUTPUT (raw code only, NO markdown):\n"
    )
```

---

### Phân tích Prompt Structure

**Section 1: Persona**
```python
f"You are an expert {seq.language} code completion AI assistant.\n"
"Your ONLY job is to complete the code at the cursor position.\n\n"
```

**Example:**
```
You are an expert python code completion AI assistant.
Your ONLY job is to complete the code at the cursor position.
```

---

**Section 2: Rules**
```python
"RULES (follow ALL strictly):\n- " + "\n- ".join(rules) + "\n\n"
```

**Output:**
```
RULES (follow ALL strictly):
- Return ONLY the missing python code that should appear at the cursor position.
- CRITICAL: Never use markdown code blocks, backticks (```), or any formatting markers.
- Output must be pure, executable code that can be inserted directly into the file.
...
```

---

**Section 3: Examples**
```python
+ examples +
```

**Includes all 3 examples with <prefix>/<suffix> format**

---

**Section 4: Actual task**
```python
"NOW complete the following code at <cursor/> position:\n\n"
f"<prefix>\n{seq.prefix}\n</prefix>\n\n"
f"<suffix>\n{seq.suffix}\n</suffix>\n\n"
"<cursor/>\n\n"
```

**Example:**
```
NOW complete the following code at <cursor/> position:

<prefix>
def calculate_sum(numbers):
    
</prefix>

<suffix>

result = calculate_sum([1, 2, 3])
</suffix>

<cursor/>
```

---

**Section 5: Output marker**
```python
"OUTPUT (raw code only, NO markdown):\n"
```

**Final reminder** before LLM generates!

---

### Complete Prompt Example

```
You are an expert python code completion AI assistant.
Your ONLY job is to complete the code at the cursor position.

RULES (follow ALL strictly):
- Return ONLY the missing python code that should appear at the cursor position.
- CRITICAL: Never use markdown code blocks, backticks (```), or any formatting markers.
- Output must be pure, executable code that can be inserted directly into the file.
- Do not add explanations, comments, or docstrings unless they are part of the actual code logic.
- Respect the exact indentation from the last line before the cursor.
- Do not repeat any code that already exists in the prefix or suffix.
- If the prefix ends with ':', indent the completion by 4 spaces (Python block).
- Keep completions concise but complete - finish the current logical block.

EXAMPLE 1 - Function body completion:
<prefix>
def add(a, b):
    
</prefix>
<suffix>

def multiply(x, y):
</suffix>
CORRECT OUTPUT:
    return a + b

... (more examples) ...

NOW complete the following code at <cursor/> position:

<prefix>
def fibonacci(n):
    
</prefix>

<suffix>

result = fibonacci(10)
</suffix>

<cursor/>

OUTPUT (raw code only, NO markdown):

```

**LLM generates:**
```python
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

---

## 🌐 Function: `call_generate()`

### Purpose
**Call Ollama API** để generate code completion

### Function Signature

```python
def call_generate(prompt: str, max_tokens: int, temperature: float, stop, stream: bool):
```

**Parameters:**
- `prompt`: Prompt string từ build_prompt()
- `max_tokens`: Max tokens to generate
- `temperature`: Sampling temperature (0.0-1.0)
- `stop`: Stop sequences (list)
- `stream`: Streaming mode (True/False)

---

### Step 1: Build Request Body

```python
    body = {
        "model": settings.MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": float(temperature),
            "num_ctx": getattr(settings, "NUM_CTX", 4096),  # Increased from 2048 to 4096
            "num_predict": int(max_tokens),
            "repeat_penalty": 1.1,
            "stop": stop,
            "top_p": 0.9,  # Add top_p for better quality
            "top_k": 40,   # Add top_k sampling
        },
    }
```

---

### Phân tích Request Body

#### Top-level fields

```python
"model": settings.MODEL,  # e.g., "deepseek-coder:6.7b"
"prompt": prompt,         # Full prompt string
"stream": stream,         # True for SSE streaming, False for complete response
```

---

#### Options object

**temperature**
```python
"temperature": float(temperature),
```

**Range:** 0.0 (deterministic) - 1.0 (creative)
**Default:** 0.2 (for code completion)

**Effect:**
- 0.0: Always picks most likely token (deterministic)
- 0.2: Slight variation (good for code)
- 0.5: Balanced
- 1.0: Very creative (not good for code!)

---

**num_ctx**
```python
"num_ctx": getattr(settings, "NUM_CTX", 4096),  # Increased from 2048 to 4096
```

**Context window size:**
- Old: 2048 tokens (~1500 words)
- New: 4096 tokens (~3000 words)
- Allows longer prefix/suffix

**Why increase?**
- Support larger files
- More context = better completions
- Modern models support it

---

**num_predict**
```python
"num_predict": int(max_tokens),
```

**Maximum tokens to generate**
- Default: 128 tokens (~100 words)
- Limits completion length

---

**repeat_penalty**
```python
"repeat_penalty": 1.1,
```

**Penalty for repeating tokens:**
- 1.0 = No penalty
- 1.1 = Slight penalty (prevents repetition)
- 1.5 = Strong penalty

**Why 1.1?**
- Code often has repetition (loops, patterns)
- Too high penalty breaks valid code
- 1.1 is balanced

---

**stop**
```python
"stop": stop,
```

**Stop sequences:**
```python
stop = ["\ndef ", "\nclass ", "\n#"]
# LLM stops generating when encountering these
```

**Example:**
```python
# LLM generates:
def add(a, b):
    return a + b

def  ← Stops here (detected "\ndef ")
```

---

**top_p (nucleus sampling)**
```python
"top_p": 0.9,  # Add top_p for better quality
```

**How it works:**
1. Sort tokens by probability
2. Take tokens until cumulative probability ≥ 0.9
3. Sample from this subset

**Example:**
```
Token probabilities:
return: 50%
pass: 30%
yield: 15%
raise: 3%
others: 2%

top_p=0.9:
Consider: return (50%), pass (30%), yield (15%) = 95% ≥ 90% ✅
Ignore: raise, others
```

**Benefit:** Cuts off very unlikely tokens (reduces nonsense)

---

**top_k**
```python
"top_k": 40,   # Add top_k sampling
```

**Simpler than top_p:**
- Consider only top 40 most likely tokens
- Ignore all others

**Example:**
```
Vocabulary: 50,000 tokens
top_k=40: Only consider 40 most likely
```

**Benefit:** Faster, prevents rare/weird tokens

---

### Step 2: Prepare Headers

```python
    # Build headers: if an Ollama API key is configured, attach Authorization header
    headers = {}
    if getattr(settings, "OLLAMA_API_KEY", None):
        # Ollama Cloud typically expects a Bearer token
        headers["Authorization"] = f"Bearer {settings.OLLAMA_API_KEY}"
```

---

#### Conditional API Key

```python
if getattr(settings, "OLLAMA_API_KEY", None):
```

**Two scenarios:**

**Scenario 1: Local Ollama (no API key)**
```python
# .env:
OLLAMA_URL=http://localhost:11434

# Code:
getattr(settings, "OLLAMA_API_KEY", None)  # → None
headers = {}  # Empty headers (no auth needed)
```

**Scenario 2: Ollama Cloud (with API key)**
```python
# .env:
OLLAMA_URL=https://api.ollama.com
OLLAMA_API_KEY=olk_abc123xyz...

# Code:
getattr(settings, "OLLAMA_API_KEY", None)  # → "olk_abc123xyz..."
headers = {"Authorization": "Bearer olk_abc123xyz..."}
```

---

#### getattr() for Backward Compatibility

```python
getattr(settings, "OLLAMA_API_KEY", None)
```

**Why not `settings.OLLAMA_API_KEY`?**
- Old configs don't have OLLAMA_API_KEY
- Would raise AttributeError
- `getattr()` returns `None` if missing (safe!)

**Backward compatible:**
```python
# Old config (no OLLAMA_API_KEY):
getattr(settings, "OLLAMA_API_KEY", None)  # → None (works!)

# New config (has OLLAMA_API_KEY):
getattr(settings, "OLLAMA_API_KEY", None)  # → "olk_..." (works!)
```

---

### Step 3: Build URL

```python
    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/generate"
```

---

#### rstrip('/') for URL Safety

```python
settings.OLLAMA_URL.rstrip('/')
```

**Handles trailing slashes:**

```python
# Config has trailing slash:
OLLAMA_URL = "http://localhost:11434/"
url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
# → "http://localhost:11434/api/generate" ✅

# Config without trailing slash:
OLLAMA_URL = "http://localhost:11434"
url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
# → "http://localhost:11434/api/generate" ✅
```

**Prevents double slash:**
```python
# Without rstrip():
"http://localhost:11434/" + "/api/generate"
# → "http://localhost:11434//api/generate" ❌ (double slash!)

# With rstrip():
"http://localhost:11434/".rstrip('/') + "/api/generate"
# → "http://localhost:11434/api/generate" ✅
```

---

### Step 4: Make HTTP Request

```python
    try:
        resp = SESSION.post(url, json=body, timeout=TIMEOUT, stream=stream, headers=headers or None)
```

---

#### SESSION from core.http

```python
from app.core.http import SESSION, TIMEOUT
```

**Shared HTTP session:**
- Reuses TCP connections (faster!)
- Configured retry logic
- Shared across all requests

**See:** `explaincode/core/02_http.py.md`

---

#### Parameters

```python
SESSION.post(
    url,                    # "http://localhost:11434/api/generate"
    json=body,              # Auto-serialize to JSON
    timeout=TIMEOUT,        # 30 seconds (from settings)
    stream=stream,          # True for streaming, False for complete
    headers=headers or None # Authorization header (if needed)
)
```

**`headers or None`:**
```python
# If headers is empty:
headers = {}
headers or None  # → None

# If headers has content:
headers = {"Authorization": "Bearer ..."}
headers or None  # → {"Authorization": "Bearer ..."}
```

**Why?**
- `requests.post(..., headers=None)` = no custom headers
- `requests.post(..., headers={})` = empty headers dict
- Cleaner to pass `None` when no headers needed

---

### Step 5: Handle Network Errors

```python
    except Exception as exc:  # network/connection errors
        logger.exception("Error while calling Ollama at %s", settings.OLLAMA_URL)
        raise HTTPException(status_code=502, detail={"ollama_error": str(exc)})
```

---

#### Broad Exception Catching

```python
except Exception as exc:
```

**Catches:**
- `requests.exceptions.Timeout`: Request took too long
- `requests.exceptions.ConnectionError`: Can't reach server
- `requests.exceptions.RequestException`: Any requests error
- Any Python exception

**Why so broad?**
- Network issues are unpredictable
- Better to catch all and log
- Return 502 (Bad Gateway) to client

---

#### Logging

```python
logger.exception("Error while calling Ollama at %s", settings.OLLAMA_URL)
```

**Output example:**
```
[ERROR] Error while calling Ollama at http://localhost:11434
Traceback (most recent call last):
  File "ollama.py", line 123, in call_generate
    resp = SESSION.post(...)
  requests.exceptions.ConnectionError: Failed to establish connection
```

**`logger.exception()`:**
- Logs at ERROR level
- Includes full traceback
- Useful for debugging

---

#### Return 502 Bad Gateway

```python
raise HTTPException(status_code=502, detail={"ollama_error": str(exc)})
```

**502 = Upstream service failed:**
- Our server is OK
- External service (Ollama) failed
- Client receives:
```json
{
  "detail": {
    "ollama_error": "Failed to establish connection to http://localhost:11434"
  }
}
```

---

### Step 6: Handle HTTP Errors

```python
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=502, detail={"ollama_error": detail})
```

---

#### Check Status Code

```python
if resp.status_code >= 400:
```

**Error codes from Ollama:**
- `400`: Bad Request (invalid model/parameters)
- `404`: Not Found (model doesn't exist)
- `500`: Internal Server Error (Ollama crashed)
- `503`: Service Unavailable (Ollama overloaded)

---

#### Try to Parse JSON Error

```python
try:
    detail = resp.json()
except Exception:
    detail = resp.text
```

**Ollama usually returns JSON errors:**
```json
{
  "error": "model 'invalid-model' not found"
}
```

**But sometimes plain text:**
```
Internal Server Error
```

**This code handles both!**

---

#### Return Error to Client

```python
raise HTTPException(status_code=502, detail={"ollama_error": detail})
```

**Client receives:**
```json
{
  "detail": {
    "ollama_error": {
      "error": "model 'invalid-model' not found"
    }
  }
}
```

---

### Step 7: Return Response

```python
    return resp
```

**Returns `requests.Response` object:**
- For non-streaming: Full response ready
- For streaming: Response object with `.iter_lines()` for SSE

**Used by caller:**
```python
# Non-streaming:
resp = call_generate(prompt, 100, 0.2, [], False)
data = resp.json()
completion = data["response"]

# Streaming:
resp = call_generate(prompt, 100, 0.2, [], True)
for line in resp.iter_lines():
    chunk = json.loads(line)
    yield chunk["response"]
```

---

## 🔧 Function: `generate_completion()`

### Purpose
**Public shim** expected by tests

### Code

```python
def generate_completion(*args, **kwargs) -> str:
    """
    Public entry expected by tests. If you already have an internal function that
    does the actual work (e.g., _generate_completion or complete_once), delegate to it.
    Otherwise this will raise until wired up — tests will monkeypatch it anyway.
    """
    try:
        # Nếu bạn đã có hàm thật, đổi tên ở đây cho đúng:
        return _generate_completion(*args, **kwargs)  # type: ignore[name-defined]
    except NameError:
        raise RuntimeError("generate_completion is not wired to an internal impl yet")
```

---

### Phân tích

#### Test Compatibility Layer

**Purpose:**
- Tests expect `generate_completion()` function
- But actual implementation may be named differently
- This provides stable interface

**Example usage in tests:**
```python
from app.services.ollama import generate_completion

# Test can mock this:
with patch('app.services.ollama.generate_completion', return_value="test code"):
    result = some_function_that_uses_ollama()
```

---

#### Delegation Pattern

```python
try:
    return _generate_completion(*args, **kwargs)  # type: ignore[name-defined]
except NameError:
    raise RuntimeError("generate_completion is not wired to an internal impl yet")
```

**Tries to call internal implementation:**
- If `_generate_completion()` exists → delegate to it
- If not found (NameError) → raise clear error

**`# type: ignore[name-defined]`:**
- Suppress mypy error
- We know function might not exist

---

#### Alternative: Direct Implementation

**Could also be implemented as:**
```python
def generate_completion(prompt: str, max_tokens: int, temperature: float, stop: list) -> str:
    resp = call_generate(prompt, max_tokens, temperature, stop, stream=False)
    data = resp.json()
    return data["response"]
```

**But current approach:**
- More flexible
- Allows internal refactoring
- Tests can still mock

---

## 🆔 Function: `new_request_id()`

### Purpose
**Generate unique request ID** (same as Groq service)

### Code

```python
def new_request_id() -> str:
    return str(uuid.uuid4())[:8]
```

**Identical to groq.py implementation!**

**See:** `explaincode/services/01_groq.py.md` for detailed explanation

**Example:**
```python
req_id = new_request_id()
# → "f3a2b1c7"

logger.info(f"[{req_id}] Processing Ollama request")
# → [INFO] [f3a2b1c7] Processing Ollama request
```

---

## 💡 Key Points cho thuyết trình

### 1. Ollama vs Groq

**Comparison table:**

| Feature | Ollama | Groq |
|---------|--------|------|
| **Deployment** | Local/Self-hosted | Cloud (SaaS) |
| **Speed** | Depends on hardware | Very fast (LPU) |
| **Cost** | Free (own hardware) | Free tier (limited) |
| **Privacy** | 100% private (local) | Data sent to cloud |
| **Setup** | Install + download models | Just API key |
| **Models** | All open-source models | Curated selection |
| **Reliability** | Depends on hardware | 99.9% uptime |

**Use cases:**

**Choose Ollama when:**
- ✅ Privacy critical (sensitive code)
- ✅ No internet/restricted network
- ✅ Have good hardware (GPU)
- ✅ Want specific models

**Choose Groq when:**
- ✅ Need fast response (<1s)
- ✅ Don't want to manage infrastructure
- ✅ Want latest models
- ✅ Need reliability/uptime

---

### 2. Prompt Engineering Differences

**Ollama prompt simpler than Groq:**

| Aspect | Ollama | Groq |
|--------|--------|------|
| **System message** | Simple persona | Detailed with critical rules |
| **Examples** | 3 basic examples | 4 detailed examples per language |
| **Language rules** | None | PEP 8, C++ guidelines |
| **User hints** | Not included | User profiling integration |
| **Format** | <prefix>/<suffix>/<cursor/> | <PREFIX>/<SUFFIX>/<FILL> |

**Why simpler?**
- Ollama models smaller (6.7B vs 70B)
- Too detailed prompt confuses smaller models
- Focus on core rules only

---

### 3. Ollama API Format

**Ollama uses `/api/generate` endpoint:**

**Request:**
```json
{
  "model": "deepseek-coder:6.7b",
  "prompt": "Complete this code...",
  "stream": false,
  "options": {
    "temperature": 0.2,
    "num_ctx": 4096,
    "num_predict": 128,
    "stop": ["\ndef "]
  }
}
```

**Response:**
```json
{
  "model": "deepseek-coder:6.7b",
  "created_at": "2025-11-11T10:30:00Z",
  "response": "    return a + b\n",
  "done": true,
  "context": [123, 456, ...],
  "total_duration": 500000000,
  "load_duration": 100000000,
  "prompt_eval_duration": 200000000,
  "eval_duration": 200000000
}
```

---

### 4. Streaming Support

**Ollama supports SSE streaming:**

**Request:**
```json
{
  "stream": true,
  ...
}
```

**Response (multiple chunks):**
```
{"response": "    return", "done": false}
{"response": " a", "done": false}
{"response": " +", "done": false}
{"response": " b", "done": false}
{"response": "\n", "done": true}
```

**Benefits:**
- Show completion as it's generated
- Better UX (feels faster)
- Can cancel mid-generation

**Implementation:**
```python
resp = call_generate(prompt, max_tokens, temp, stop, stream=True)
for line in resp.iter_lines():
    chunk = json.loads(line)
    if chunk["response"]:
        yield chunk["response"]
    if chunk["done"]:
        break
```

---

### 5. Advanced Sampling Parameters

**Ollama supports fine-tuned control:**

**temperature (diversity)**
```python
0.0  # Deterministic (always same output)
0.2  # Slight variation (code completion) ✅
0.5  # Balanced
1.0  # Very creative (writing)
```

**top_p (nucleus sampling)**
```python
0.9  # Consider tokens up to 90% cumulative probability
```

**top_k (top-k sampling)**
```python
40  # Consider only top 40 tokens
```

**repeat_penalty**
```python
1.0  # No penalty
1.1  # Slight penalty (prevents loops) ✅
1.5  # Strong penalty
```

**Combination:**
```python
{
  "temperature": 0.2,  # Low randomness
  "top_p": 0.9,        # Cut tail
  "top_k": 40,         # Limit choices
  "repeat_penalty": 1.1  # Avoid repetition
}
# → High quality, diverse, non-repetitive code ✅
```

---

## 🧪 Test Cases

### Test 1: Build prompt

```python
from app.schemas.completion import CompleteRequest

req = CompleteRequest(
    prefix="def add(a, b):\n    ",
    suffix="\n\nprint('test')",
    language="python"
)

prompt = build_prompt(req)

assert "expert python code completion" in prompt.lower()
assert "<prefix>" in prompt
assert "def add(a, b):" in prompt
assert "<suffix>" in prompt
assert "print('test')" in prompt
assert "<cursor/>" in prompt
assert "RULES" in prompt
assert "EXAMPLE 1" in prompt
```

---

### Test 2: Call Ollama (mocked success)

```python
from unittest.mock import Mock, patch

mock_response = Mock()
mock_response.status_code = 200
mock_response.json.return_value = {
    "response": "return a + b",
    "done": True
}

with patch('app.core.http.SESSION.post', return_value=mock_response) as mock_post:
    resp = call_generate("test prompt", 100, 0.2, ["\ndef "], False)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "return a + b"
    
    # Check request was correct:
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args.kwargs["json"]["model"] == settings.MODEL
    assert call_args.kwargs["json"]["prompt"] == "test prompt"
    assert call_args.kwargs["json"]["stream"] is False
```

---

### Test 3: Handle Ollama error

```python
mock_response = Mock()
mock_response.status_code = 404
mock_response.json.return_value = {"error": "model not found"}

with patch('app.core.http.SESSION.post', return_value=mock_response):
    with pytest.raises(HTTPException) as exc:
        call_generate("test", 100, 0.2, [], False)
    
    assert exc.value.status_code == 502
    assert "ollama_error" in exc.value.detail
    assert "model not found" in str(exc.value.detail)
```

---

### Test 4: Handle network error

```python
import requests

with patch('app.core.http.SESSION.post', side_effect=requests.exceptions.ConnectionError("Connection refused")):
    with pytest.raises(HTTPException) as exc:
        call_generate("test", 100, 0.2, [], False)
    
    assert exc.value.status_code == 502
    assert "ollama_error" in exc.value.detail
    assert "Connection refused" in str(exc.value.detail)
```

---

### Test 5: Streaming response

```python
def mock_iter_lines():
    yield b'{"response": "return", "done": false}'
    yield b'{"response": " a + b", "done": false}'
    yield b'{"response": "", "done": true}'

mock_response = Mock()
mock_response.status_code = 200
mock_response.iter_lines.return_value = mock_iter_lines()

with patch('app.core.http.SESSION.post', return_value=mock_response):
    resp = call_generate("test", 100, 0.2, [], stream=True)
    
    chunks = []
    for line in resp.iter_lines():
        chunk = json.loads(line)
        if chunk["response"]:
            chunks.append(chunk["response"])
    
    assert "".join(chunks) == "return a + b"
```

---

### Test 6: API key header

```python
# Test with API key:
with patch('app.core.config.settings') as mock_settings:
    mock_settings.OLLAMA_API_KEY = "olk_test123"
    mock_settings.OLLAMA_URL = "https://api.ollama.com"
    mock_settings.MODEL = "llama2"
    
    mock_response = Mock()
    mock_response.status_code = 200
    
    with patch('app.core.http.SESSION.post', return_value=mock_response) as mock_post:
        call_generate("test", 100, 0.2, [], False)
        
        # Check Authorization header was sent:
        call_args = mock_post.call_args
        headers = call_args.kwargs["headers"]
        assert headers is not None
        assert headers["Authorization"] == "Bearer olk_test123"

# Test without API key:
with patch('app.core.config.settings') as mock_settings:
    del mock_settings.OLLAMA_API_KEY  # No API key
    mock_settings.OLLAMA_URL = "http://localhost:11434"
    
    mock_response = Mock()
    mock_response.status_code = 200
    
    with patch('app.core.http.SESSION.post', return_value=mock_response) as mock_post:
        call_generate("test", 100, 0.2, [], False)
        
        # Check no headers sent:
        call_args = mock_post.call_args
        headers = call_args.kwargs["headers"]
        assert headers is None
```

---

### Test 7: URL formatting

```python
# Test trailing slash handling:
with patch('app.core.config.settings') as mock_settings:
    mock_settings.OLLAMA_URL = "http://localhost:11434/"  # Trailing slash
    
    mock_response = Mock()
    mock_response.status_code = 200
    
    with patch('app.core.http.SESSION.post', return_value=mock_response) as mock_post:
        call_generate("test", 100, 0.2, [], False)
        
        # Check URL was correct (no double slash):
        call_args = mock_post.call_args
        url = call_args.args[0]
        assert url == "http://localhost:11434/api/generate"
        assert "//" not in url.replace("http://", "")  # No double slash
```

---

**File ollama.py hoàn tất!** ✅

**Tiếp theo:** `user_profiling.py` (326 lines - file phức tạp với ML-style analysis). Tiếp tục không? 🚀

