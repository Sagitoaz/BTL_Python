# Giải thích chi tiết: `server/app/schemas/completion.py`

## 📋 Mục đích của file

File này define **Pydantic Models** cho completion API:
1. **Request validation** (CompleteRequest)
2. **Response structure** (CompleteResponse)
3. **Default constants** (stop sequences, tokens, temperature)
4. **Data sanitization** (validators)
5. **Type safety** cho FastAPI endpoints

---

## 🔍 Phân tích từng phần

### Import statements

```python
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
```

**Giải thích:**

- `Literal`: Type hint cho giá trị cố định (enum-like)
- `BaseModel`: Pydantic base class cho models
- `Field`: Define field với validation rules
- `field_validator`: Validate individual fields
- `model_validator`: Validate entire model after parsing

---

## 🎯 Constants: Stop Sequences

### Python Stop Sequences

```python
# Groq API only allows max 4 stop sequences
DEFAULT_STOPS_PY = ["\n\n```", "\n\n##", '\n\n"""', "\n\n'''"]
```

---

### Phân tích chi tiết

#### Comment: Groq Limitation

```python
# Groq API only allows max 4 stop sequences
```

**Important constraint:**
- Groq API limit: Maximum 4 stop sequences
- Must choose carefully
- More stops = more precise termination

---

#### Stop Sequence 1: `"\n\n```"`

**Pattern:** Two newlines + three backticks

**Purpose:** Stop at markdown code fence

**Example:**
```python
# LLM generating:
def add(a, b):
    return a + b

```python  ← STOP HERE (markdown code block start)
```

**Why?**
- LLMs trained on markdown might continue with "```python"
- We want just the code, not markdown

---

#### Stop Sequence 2: `"\n\n##"`

**Pattern:** Two newlines + two hash symbols

**Purpose:** Stop at markdown heading

**Example:**
```python
# LLM generating:
def add(a, b):
    return a + b

## Next Section  ← STOP HERE (markdown heading)
```

**Why?**
- Prevents generating documentation sections
- Focuses on code only

---

#### Stop Sequence 3: `'\n\n"""'`

**Pattern:** Two newlines + triple double quotes

**Purpose:** Stop at docstring start

**Example:**
```python
# LLM generating:
def add(a, b):
    return a + b

"""  ← STOP HERE (docstring start)
This is a docstring
"""
```

**Why?**
- Prevents generating unrelated docstrings
- User might want to write their own docs

---

#### Stop Sequence 4: `"\n\n'''"`

**Pattern:** Two newlines + triple single quotes

**Purpose:** Stop at alternate docstring style

**Example:**
```python
# LLM generating:
def add(a, b):
    return a + b

'''  ← STOP HERE (alternate docstring)
This is a docstring
'''
```

**Why?**
- Same as `"""` but for single-quote style
- Both are valid Python docstrings

---

### C/C++ Stop Sequences

```python
DEFAULT_STOPS_CPP = ["\n\n```", "\n\n//", "\n\n/*", "\n\n#endif"]
```

---

#### Stop Sequence 1: `"\n\n```"`

**Same as Python:** Stop at markdown fence

---

#### Stop Sequence 2: `"\n\n//"`

**Pattern:** Two newlines + double slash

**Purpose:** Stop at C++ comment block

**Example:**
```cpp
// LLM generating:
int add(int a, int b) {
    return a + b;
}

// This is a comment  ← STOP HERE
```

**Why?**
- Comment blocks might be unrelated
- Focus on code implementation

---

#### Stop Sequence 3: `"\n\n/*"`

**Pattern:** Two newlines + slash-star

**Purpose:** Stop at multi-line comment start

**Example:**
```cpp
// LLM generating:
int add(int a, int b) {
    return a + b;
}

/*  ← STOP HERE (multi-line comment)
 * Comment block
 */
```

---

#### Stop Sequence 4: `"\n\n#endif"`

**Pattern:** Two newlines + preprocessor directive

**Purpose:** Stop at preprocessor block end

**Example:**
```cpp
// LLM generating:
int add(int a, int b) {
    return a + b;
}

#endif  ← STOP HERE (preprocessor)
```

**Why?**
- Prevents generating unrelated preprocessor blocks
- Keeps completion focused

---

## 🔢 Default Values

```python
DEFAULT_MAX_TOKENS = 128
DEFAULT_TEMPERATURE = 0.2
```

---

### `DEFAULT_MAX_TOKENS = 128`

**Purpose:** Maximum tokens to generate

**Why 128?**
- Enough for most single completions (3-5 lines)
- Not too long (prevents rambling)
- Fast response time

**Token examples:**
```python
# ~30 tokens:
def add(a, b):
    return a + b

# ~100 tokens:
def calculate_average(numbers: List[float]) -> float:
    """Calculate average of a list of numbers."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
```

**Balance:**
- Too few tokens (20): Incomplete code
- Too many tokens (500): Slow, unnecessary

---

### `DEFAULT_TEMPERATURE = 0.2`

**Purpose:** Randomness in generation

**Scale:** 0.0 (deterministic) to 1.0 (creative)

**Why 0.2?**
- Low temperature → more predictable
- Good for code (want consistency)
- Not 0.0 → allows some variation

**Temperature effects:**

**Temperature 0.0:**
```python
# Always generates:
def add(a, b):
    return a + b
```

**Temperature 0.2 (our default):**
```python
# Might generate:
def add(a, b):
    return a + b

# Or:
def add(a, b):
    return (a + b)

# Or:
def add(a, b):
    result = a + b
    return result
```

**Temperature 1.0:**
```python
# Might generate (too creative):
def add(a, b):
    # Calculate sum using advanced algorithm
    intermediate = a
    intermediate += b
    return intermediate  # Return computed result
```

---

## 📥 Model: `CompleteRequest`

### Purpose
**Request validation model** cho completion endpoints

### Code Overview

```python
class CompleteRequest(BaseModel):
    prefix: str = ""
    suffix: str = ""
    language: Literal[
        "python", "javascript", "typescript", "java", "c", "cpp", "c++", "go", "rust", "kotlin", ""
    ] = "python"
    max_tokens: int = Field(DEFAULT_MAX_TOKENS, ge=1, le=512)
    temperature: float = Field(DEFAULT_TEMPERATURE, ge=0.0, le=1.0)
    stop: list[str] | None = None
    comment_instruction: str | None = None  # For comment-to-code generation

    code_only: bool = True
```

---

## 📝 Field: `prefix`

```python
    prefix: str = ""
```

**Type:** `str`

**Default:** Empty string `""`

**Purpose:** Code before cursor position

**Example:**
```python
# User typing:
def add(a, b):
    |  ← Cursor here

# prefix:
"def add(a, b):\n    "
```

**Use case:**
- Context for completion
- Used in FIM (Fill-In-the-Middle) prompt

---

## 📝 Field: `suffix`

```python
    suffix: str = ""
```

**Type:** `str`

**Default:** Empty string `""`

**Purpose:** Code after cursor position

**Example:**
```python
# User typing:
def add(a, b):
    |  ← Cursor here

print('test')

# suffix:
"\n\nprint('test')"
```

**Use case:**
- Context for completion
- Helps LLM understand what comes after
- Better completions (knows not to generate print statement)

---

## 📝 Field: `language`

```python
    language: Literal[
        "python", "javascript", "typescript", "java", "c", "cpp", "c++", "go", "rust", "kotlin", ""
    ] = "python"
```

---

### Phân tích chi tiết

#### `Literal[...]`

**Purpose:** Restrict to specific values only

**Allowed values:**
```python
"python"      # Python
"javascript"  # JavaScript
"typescript"  # TypeScript
"java"        # Java
"c"           # C
"cpp"         # C++
"c++"         # C++ (alternate)
"go"          # Go
"rust"        # Rust
"kotlin"      # Kotlin
""            # Empty (auto-detect)
```

**Validation:**
```python
# Valid:
{"language": "python"}  ✅
{"language": "typescript"}  ✅

# Invalid:
{"language": "ruby"}  ❌
# → ValidationError: Input should be 'python', 'javascript', ...
```

---

#### Default: `"python"`

**Why Python default?**
- Most popular language for AI/ML
- Project primary language
- Safe fallback

---

## 📝 Field: `max_tokens`

```python
    max_tokens: int = Field(DEFAULT_MAX_TOKENS, ge=1, le=512)
```

---

### Phân tích chi tiết

#### `Field(DEFAULT_MAX_TOKENS, ...)`

**Default value:** `128` (from constant)

#### `ge=1`

**Greater than or equal to 1**

**Validation:**
```python
{"max_tokens": 1}    ✅
{"max_tokens": 100}  ✅
{"max_tokens": 0}    ❌  # Too small
{"max_tokens": -5}   ❌  # Negative
```

**Why minimum 1?**
- Need at least some output
- 0 tokens = no completion

---

#### `le=512`

**Less than or equal to 512**

**Validation:**
```python
{"max_tokens": 512}  ✅
{"max_tokens": 256}  ✅
{"max_tokens": 513}  ❌  # Too large
{"max_tokens": 1000} ❌  # Too large
```

**Why maximum 512?**
- Performance (faster response)
- Cost (fewer tokens = cheaper)
- Typical completion length (most are < 512 tokens)
- Prevents LLM rambling

---

## 📝 Field: `temperature`

```python
    temperature: float = Field(DEFAULT_TEMPERATURE, ge=0.0, le=1.0)
```

---

### Phân tích chi tiết

#### `Field(DEFAULT_TEMPERATURE, ...)`

**Default value:** `0.2` (from constant)

#### `ge=0.0`

**Greater than or equal to 0.0**

**Minimum:** 0.0 (completely deterministic)

---

#### `le=1.0`

**Less than or equal to 1.0**

**Maximum:** 1.0 (maximum creativity)

**Validation:**
```python
{"temperature": 0.0}   ✅  # Deterministic
{"temperature": 0.2}   ✅  # Low (default)
{"temperature": 0.7}   ✅  # Medium
{"temperature": 1.0}   ✅  # High
{"temperature": 1.5}   ❌  # Too high
{"temperature": -0.1}  ❌  # Negative
```

---

## 📝 Field: `stop`

```python
    stop: list[str] | None = None
```

---

### Phân tích chi tiết

#### Type: `list[str] | None`

**Union type:**
- Can be list of strings: `["stop1", "stop2"]`
- Can be `None`: No custom stops

**Default:** `None`

---

#### Purpose

**Custom stop sequences** (in addition to defaults)

**Example:**
```python
# Request with custom stops:
{
    "prefix": "def add(",
    "language": "python",
    "stop": ["\nTODO", "\nFIXME"]
}

# Effective stops:
# DEFAULT_STOPS_PY + custom
# ["\n\n```", "\n\n##", ...] + ["\nTODO", "\nFIXME"]
```

**Use case:**
- Project-specific patterns
- Stop at TODO comments
- Stop at specific keywords

---

## 📝 Field: `comment_instruction`

```python
    comment_instruction: str | None = None  # For comment-to-code generation
```

---

### Phân tích chi tiết

#### Type: `str | None`

**Optional field** for comment-to-code feature

#### Purpose

**Convert comment to code**

**Example:**
```python
# User types comment:
# Calculate factorial of n

# Request:
{
    "prefix": "# Calculate factorial of n\n",
    "comment_instruction": "Calculate factorial of n",
    "language": "python"
}

# LLM generates:
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

**Use case:**
- Docstring-to-code
- Comment-driven development
- Quick prototyping

---

## 📝 Field: `code_only`

```python
    code_only: bool = True
```

**Type:** `bool`

**Default:** `True`

**Purpose:** Strip markdown and explanations

**Example:**

**`code_only = True` (default):**
```python
# LLM output:
```python
def add(a, b):
    return a + b
```

# After processing:
"def add(a, b):\n    return a + b"  # Clean code only
```

**`code_only = False`:**
```python
# LLM output preserved as-is (might include explanations)
```

---

## 🔧 Validator: `sanitize_stops`

### Purpose
**Clean and validate stop sequences**

### Code

```python
    @field_validator("stop", mode="before")
    @classmethod
    def sanitize_stops(cls, v: list[str] | None):
        if v is None:
            return None
        return [s for s in v if isinstance(s, str) and s]
```

---

### Phân tích chi tiết

#### Decorator: `@field_validator("stop", mode="before")`

**Purpose:**
- Validate `stop` field
- Run BEFORE Pydantic's type validation
- Can modify value before type checking

**`mode="before"`:**
- Raw input value (not yet converted)
- Can handle invalid types gracefully

---

#### Check None

```python
        if v is None:
            return None
```

**If no stops provided → return None (valid)**

---

#### Filter Invalid Stops

```python
        return [s for s in v if isinstance(s, str) and s]
```

**List comprehension breakdown:**

**`for s in v`:**
- Loop each item in list

**`isinstance(s, str)`:**
- Check if item is string
- Filter out non-strings (numbers, objects, etc.)

**`and s`:**
- Check if string is not empty
- Filter out empty strings `""`

---

### Example Transformations

**Input: Valid stops**
```python
v = ["\nTODO", "\nFIXME"]
# Output: ["\nTODO", "\nFIXME"]  ✅
```

**Input: Mixed types**
```python
v = ["\nTODO", 123, None, "\nFIXME"]
# Filter: isinstance(s, str) and s
# Output: ["\nTODO", "\nFIXME"]  ✅ (123 and None removed)
```

**Input: Empty strings**
```python
v = ["\nTODO", "", "  ", "\nFIXME"]
# Filter: s (truthy check)
# Output: ["\nTODO", "  ", "\nFIXME"]  (empty string removed)
```

**Input: All invalid**
```python
v = [123, None, ""]
# Output: []  (empty list, all filtered out)
```

---

## 🔧 Validator: `normalize_language`

### Purpose
**Normalize language to lowercase**

### Code

```python
    @model_validator(mode="after")
    def normalize_language(self):
        if self.language:
            self.language = self.language.lower()
        return self
```

---

### Phân tích chi tiết

#### Decorator: `@model_validator(mode="after")`

**Purpose:**
- Validate entire model
- Run AFTER all fields parsed
- Can modify multiple fields

**`mode="after"`:**
- All fields already converted to correct types
- Can access `self.field_name`

---

#### Normalize to Lowercase

```python
        if self.language:
            self.language = self.language.lower()
        return self
```

**Purpose:** Case-insensitive language names

**Transformation:**
```python
# Input:
{"language": "Python"}

# After validation:
{"language": "python"}  ✅

# Input:
{"language": "TYPESCRIPT"}

# After validation:
{"language": "typescript"}  ✅
```

**Why?**
- User might type "Python", "PYTHON", "python"
- Normalize to lowercase for consistency
- Easier to compare in code

---

### Return `self`

```python
        return self
```

**Required for model validators:**
- Must return the model instance
- Allows chaining validators

---

## 📤 Model: `CompleteResponse`

### Purpose
**Response structure** cho completion endpoints

### Code

```python
class CompleteResponse(BaseModel):
    request_id: str
    completion: str
```

---

### Fields

#### `request_id: str`

**Purpose:** Unique identifier for request

**Example:**
```python
"request_id": "550e8400-e29b-41d4-a716-446655440000"
```

**Use case:**
- Debugging (track request in logs)
- Telemetry (correlate feedback)
- Client-side caching

---

#### `completion: str`

**Purpose:** Generated code completion

**Example:**
```python
"completion": "return a + b"
```

**Note:**
- Already cleaned/postprocessed
- Ready to insert into editor

---

### Example Response

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "completion": "return a + b"
}
```

---

## 📊 Diagram: Request Validation Flow

```
┌─────────────────────────────────────────────────────┐
│              Client Sends Request                    │
│  POST /complete                                     │
│  {                                                  │
│    "prefix": "def add(a, b):\n    ",               │
│    "suffix": "\n\nprint('test')",                  │
│    "language": "Python",  ← Uppercase!             │
│    "max_tokens": 100,                               │
│    "temperature": 0.2,                              │
│    "stop": ["\nTODO", "", 123, "\nFIXME"]  ← Mixed! │
│  }                                                  │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│         Pydantic Validation (Before)                 │
│                                                     │
│  1. sanitize_stops() runs first                     │
│     Input: ["\nTODO", "", 123, "\nFIXME"]          │
│     Filter non-strings and empty:                   │
│     Output: ["\nTODO", "\nFIXME"]  ✅              │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│         Pydantic Type Validation                     │
│                                                     │
│  - prefix: str ✅                                   │
│  - suffix: str ✅                                   │
│  - language: Literal[...] ✅                        │
│    "Python" in allowed values                       │
│  - max_tokens: int, 1 <= 100 <= 512 ✅             │
│  - temperature: float, 0.0 <= 0.2 <= 1.0 ✅        │
│  - stop: list[str] | None ✅                        │
│    ["\nTODO", "\nFIXME"] is valid                  │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│         Pydantic Validation (After)                  │
│                                                     │
│  2. normalize_language() runs                       │
│     self.language = "Python"                        │
│     self.language = self.language.lower()           │
│     self.language = "python"  ✅                    │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│           Validated CompleteRequest                  │
│  {                                                  │
│    "prefix": "def add(a, b):\n    ",               │
│    "suffix": "\n\nprint('test')",                  │
│    "language": "python",  ← Normalized!            │
│    "max_tokens": 100,                               │
│    "temperature": 0.2,                              │
│    "stop": ["\nTODO", "\nFIXME"],  ← Cleaned!      │
│    "comment_instruction": None,                     │
│    "code_only": True                                │
│  }                                                  │
└─────────────────────────────────────────────────────┘
```

---

## 💡 Key Points cho thuyết trình

### 1. Pydantic Benefits

**Type safety:**
```python
# Without Pydantic:
def complete(data: dict):
    max_tokens = data.get("max_tokens", 128)
    if not isinstance(max_tokens, int):  # Manual check
        raise ValueError("max_tokens must be int")
    if max_tokens < 1 or max_tokens > 512:  # Manual check
        raise ValueError("max_tokens must be 1-512")
    # ... more validation ...

# With Pydantic:
def complete(req: CompleteRequest):
    # All validation automatic! ✅
    # req.max_tokens guaranteed to be int in range [1, 512]
```

---

### 2. Stop Sequences Strategy

**Language-specific stops:**
```python
Python:  ["\n\n```", "\n\n##", '\n\n"""', "\n\n'''"]
C/C++:   ["\n\n```", "\n\n//", "\n\n/*", "\n\n#endif"]
```

**Why different?**
- Python uses docstrings (`"""`)
- C++ uses comments (`//`, `/*`)
- Tailored to language syntax

---

### 3. Default Values Reasoning

**max_tokens = 128:**
- Balance: completeness vs speed
- Most completions: 2-5 lines (~50-100 tokens)
- Extra buffer for longer completions

**temperature = 0.2:**
- Code needs consistency (not creativity)
- Not 0.0 → allows variation
- Not 0.5+ → too unpredictable

---

### 4. Validation Layers

**Three layers:**
```
1. Field validators (before) → Clean input
2. Type validators → Ensure types
3. Model validators (after) → Cross-field validation
```

**Example:**
```python
# Raw input:
{"language": "Python", "stop": ["", 123]}

# After field validator:
{"language": "Python", "stop": []}  # Cleaned

# After type validator:
{"language": "python", "stop": []}  # Types OK

# After model validator:
{"language": "python", "stop": []}  # Normalized
```

---

### 5. Error Messages

**Automatic error messages:**
```python
# Invalid language:
{"language": "ruby"}

Response:
{
  "detail": [
    {
      "loc": ["body", "language"],
      "msg": "Input should be 'python', 'javascript', 'typescript', ...",
      "type": "literal_error"
    }
  ]
}
```

**Clear for clients:**
- Exact location of error (`language` field)
- What went wrong (not in allowed values)
- What's expected (list of valid values)

---

## 🧪 Test Cases

### Test 1: Valid request (minimal)

```python
from app.schemas.completion import CompleteRequest

req = CompleteRequest(
    prefix="def add(",
    language="python"
)

assert req.prefix == "def add("
assert req.suffix == ""
assert req.language == "python"
assert req.max_tokens == 128  # Default
assert req.temperature == 0.2  # Default
```

---

### Test 2: Valid request (full)

```python
req = CompleteRequest(
    prefix="def add(a, b):\n    ",
    suffix="\n\nprint('test')",
    language="typescript",
    max_tokens=200,
    temperature=0.5,
    stop=["\nTODO", "\nFIXME"]
)

assert req.max_tokens == 200
assert req.temperature == 0.5
assert req.stop == ["\nTODO", "\nFIXME"]
```

---

### Test 3: Language normalization

```python
req = CompleteRequest(
    prefix="def add(",
    language="Python"  # Uppercase
)

assert req.language == "python"  # Normalized to lowercase

req2 = CompleteRequest(
    prefix="const x =",
    language="TypeScript"
)

assert req2.language == "typescript"
```

---

### Test 4: Stop sequences sanitization

```python
req = CompleteRequest(
    prefix="def add(",
    language="python",
    stop=["\nTODO", "", 123, None, "\nFIXME"]  # Mixed types
)

# Only valid strings kept:
assert req.stop == ["\nTODO", "\nFIXME"]
```

---

### Test 5: Validation errors

```python
from pydantic import ValidationError
import pytest

# Invalid language:
with pytest.raises(ValidationError) as exc:
    CompleteRequest(prefix="def add(", language="ruby")

assert "literal_error" in str(exc.value)

# max_tokens too high:
with pytest.raises(ValidationError) as exc:
    CompleteRequest(prefix="def add(", max_tokens=1000)

assert "less_than_equal" in str(exc.value)

# temperature out of range:
with pytest.raises(ValidationError) as exc:
    CompleteRequest(prefix="def add(", temperature=1.5)

assert "less_than_equal" in str(exc.value)
```

---

### Test 6: Response model

```python
from app.schemas.completion import CompleteResponse

resp = CompleteResponse(
    request_id="550e8400-e29b-41d4-a716-446655440000",
    completion="return a + b"
)

assert resp.request_id == "550e8400-e29b-41d4-a716-446655440000"
assert resp.completion == "return a + b"

# JSON serialization:
json_data = resp.model_dump()
assert json_data == {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "completion": "return a + b"
}
```

---

## 🔧 Usage Example

### FastAPI Endpoint Integration

```python
from fastapi import APIRouter
from app.schemas.completion import CompleteRequest, CompleteResponse

router = APIRouter()

@router.post("/complete", response_model=CompleteResponse)
def complete(req: CompleteRequest):
    # req is already validated! ✅
    # - req.language is lowercase
    # - req.stop is list of valid strings (or None)
    # - req.max_tokens is in range [1, 512]
    # - req.temperature is in range [0.0, 1.0]
    
    print(f"Language: {req.language}")
    print(f"Max tokens: {req.max_tokens}")
    print(f"Temperature: {req.temperature}")
    print(f"Stops: {req.stop}")
    
    # Generate completion...
    completion = generate(req.prefix, req.suffix)
    
    # Return validated response
    return CompleteResponse(
        request_id="abc-123",
        completion=completion
    )
```

---

### Client Example

```typescript
// TypeScript client
interface CompleteRequest {
    prefix: string;
    suffix?: string;
    language?: string;
    max_tokens?: number;
    temperature?: number;
    stop?: string[];
}

async function getCompletion(prefix: string): Promise<string> {
    const request: CompleteRequest = {
        prefix: prefix,
        suffix: "",
        language: "python",
        max_tokens: 128,
        temperature: 0.2
    };
    
    const response = await fetch('/complete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(request)
    });
    
    const data = await response.json();
    return data.completion;
}
```

---

**File này hoàn tất!** ✅

**Schemas directory hoàn tất! 1/1 file:**
- ✅ completion.py (CompleteRequest, CompleteResponse, validators)

**Tiếp theo:** `services/` directory (groq.py, user_profiling.py, ollama.py). Tiếp tục không? 🚀

