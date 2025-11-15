# Giải thích chi tiết: `server/app/services/groq.py`

## 📋 Mục đích của file

File này implement **Groq API Integration** - core AI service:
1. **Build FIM prompts** (Fill-In-the-Middle) với examples
2. **Call Groq API** cho code completion
3. **Handle errors** (timeout, rate limits, API errors)
4. **Support comment-to-code** generation
5. **User personalization** với style hints
6. **Language-specific** guidelines (Python, C++)

**Đây là file QUAN TRỌNG NHẤT** - kết nối với LLM!

---

## 🔍 Phân tích từng phần

### Import statements

```python
"""
Groq API service for code completion.
Replaces Ollama with Groq Cloud - faster, free, and always available.
"""
import logging
from typing import Optional
import uuid

from fastapi import HTTPException
import requests

from app.core.config import settings
from app.schemas.completion import CompleteRequest
```

**Giải thích:**

- `logging`: Log API calls and errors
- `Optional`: Type hint for optional parameters
- `uuid`: Generate unique request IDs
- `HTTPException`: Raise HTTP errors to client
- `requests`: HTTP client for Groq API
- `settings`: Config (API key, model, timeout)
- `CompleteRequest`: Request model

---

## 🎯 Function: `build_prompt()`

### Purpose
**Xây dựng FIM prompt** cho Groq API - QUÁ TRÌNH PHỨC TẠP NHẤT!

### Function Signature

```python
def build_prompt(req: CompleteRequest, user_style_hints: str = "") -> str:
    """
    Enhanced FIM (Fill-In-the-Middle) prompt for high-quality code completion.
    Uses proven techniques from GitHub Copilot and CodeLlama.
    Supports comment-to-code generation.
    """
```

---

### Parameters

#### `req: CompleteRequest`
- Request object chứa: prefix, suffix, language, etc.
- See: `app.schemas.completion.CompleteRequest`

#### `user_style_hints: str = ""`
- Optional personalization hints
- Example: `"Use type hints. Prefer list comprehensions."`
- From user profiling service

---

### Step 1: Detect Comment-to-Code

```python
    # Check if this is comment-to-code generation
    is_comment_to_code = req.comment_instruction is not None and len(req.comment_instruction) > 0
```

**Purpose:** Different prompt for comment → code vs normal completion

**Example:**

**Normal completion:**
```python
req.prefix = "def add(a, b):\n    "
req.comment_instruction = None
is_comment_to_code = False  # Normal completion
```

**Comment-to-code:**
```python
req.prefix = "# Calculate factorial of n\n"
req.comment_instruction = "Calculate factorial of n"
is_comment_to_code = True  # Generate code from comment
```

---

### Step 2: Build System Message (Comment-to-Code)

```python
    # Build context-aware system message
    if is_comment_to_code:
        system_msg = f"""You are an expert {req.language} code generator. Your task is to generate code based on the comment instruction.

CRITICAL RULES:
1. Read the comment instruction carefully: "{req.comment_instruction}"
2. Generate complete, working code that implements the instruction
3. Output ONLY code - NO explanations, NO markdown, NO backticks
4. The code must be syntactically correct and follow best practices
5. Match the existing code style (indentation, naming patterns)
6. Include necessary error handling and edge cases"""
```

---

### Phân tích System Message (Comment-to-Code)

#### Persona

```python
You are an expert {req.language} code generator.
```

**Purpose:**
- Set role/context for LLM
- Language-specific expertise

**Example:**
```
"You are an expert python code generator."
"You are an expert typescript code generator."
```

---

#### Task Definition

```python
Your task is to generate code based on the comment instruction.
```

**Clear objective** - not just complete, but GENERATE new code

---

#### Critical Rules

**Rule 1: Read instruction carefully**
```python
1. Read the comment instruction carefully: "{req.comment_instruction}"
```

**Inject actual instruction:**
```python
comment_instruction = "Calculate factorial of n"
# → "Read the comment instruction carefully: Calculate factorial of n"
```

---

**Rule 2: Generate complete code**
```python
2. Generate complete, working code that implements the instruction
```

**Purpose:**
- Full implementation (not stub)
- Must work (runnable)

---

**Rule 3: Output ONLY code**
```python
3. Output ONLY code - NO explanations, NO markdown, NO backticks
```

**Why critical?**

**Bad LLM output (with explanation):**
```
Here's the factorial function:

```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

This uses recursion to calculate factorial.
```

**Good LLM output (code only):**
```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

**Rule enforces clean output!**

---

**Rules 4-6: Quality constraints**
- Syntactically correct (no errors)
- Follow best practices
- Match existing style
- Include error handling

---

### Step 3: Build System Message (Normal Completion)

```python
    else:
        system_msg = f"""You are an expert {req.language} code completion engine. Your task is to complete code at the <FILL> position.

CRITICAL RULES:
1. Output ONLY the missing code - NO explanations, NO markdown, NO backticks
2. Match the existing code style EXACTLY (indentation, naming, patterns)
3. The completion must be syntactically correct and contextually appropriate
4. DO NOT repeat code from <PREFIX> or <SUFFIX>
5. Maintain proper indentation relative to surrounding code
6. Prefer concise, idiomatic solutions"""
```

---

### Phân tích System Message (Normal Completion)

#### Different persona

```python
You are an expert {req.language} code completion engine.
```

**Not generator** - specifically COMPLETION engine

---

#### Task: Fill-In-the-Middle

```python
Your task is to complete code at the <FILL> position.
```

**Clear FIM objective**

---

#### Rule 4: DO NOT repeat

```python
4. DO NOT repeat code from <PREFIX> or <SUFFIX>
```

**Critical rule!**

**Problem without this:**
```python
# PREFIX:
def add(a, b):
    

# LLM might output:
def add(a, b):  ← Repeating PREFIX!
    return a + b
```

**With rule:**
```python
# PREFIX:
def add(a, b):
    

# LLM outputs:
return a + b  ← Only the missing part!
```

---

### Step 4: Language-Specific Guidelines

```python
    # Language-specific guidelines
    if req.language == "python":
        lang_rules = """
Python Guidelines:
- Use 4 spaces for indentation (never tabs)
- Follow PEP 8 naming: snake_case for functions/variables, PascalCase for classes
- After ':' (def, class, if, for, etc.), indent the next line by 4 spaces
- Prefer list/dict comprehensions over loops when readable
- Use type hints if the surrounding code uses them"""
```

---

### Phân tích Python Guidelines

#### Indentation

```python
- Use 4 spaces for indentation (never tabs)
```

**Python standard:**
```python
def foo():
    pass  # 4 spaces

# NOT:
def foo():
	pass  # Tab (wrong!)
```

---

#### Naming Convention (PEP 8)

```python
- Follow PEP 8 naming: snake_case for functions/variables, PascalCase for classes
```

**Examples:**
```python
# snake_case (functions, variables):
def calculate_total():
my_variable = 10

# PascalCase (classes):
class UserManager:
```

---

#### Indentation After Colon

```python
- After ':' (def, class, if, for, etc.), indent the next line by 4 spaces
```

**Example:**
```python
def foo():
    ← 4 spaces indent after ':'
    
if condition:
    ← 4 spaces indent after ':'
    
for item in items:
    ← 4 spaces indent after ':'
```

---

#### List Comprehensions

```python
- Prefer list/dict comprehensions over loops when readable
```

**Good:**
```python
squares = [x**2 for x in range(10)]
```

**Avoid (when simple):**
```python
squares = []
for x in range(10):
    squares.append(x**2)
```

---

#### Type Hints

```python
- Use type hints if the surrounding code uses them
```

**Match existing style:**

**PREFIX uses type hints:**
```python
def calculate(x: int, y: int) -> int:
    # LLM should generate with type hints:
    return x + y
```

**PREFIX doesn't use type hints:**
```python
def calculate(x, y):
    # LLM should generate without:
    return x + y
```

---

### C++ Guidelines

```python
    elif req.language in ["cpp", "c++", "c"]:
        lang_rules = """
C++ Guidelines:
- Match existing indentation (usually 2 or 4 spaces, or tabs)
- Include semicolons and proper braces {} placement
- Use 'auto' for complex types when appropriate
- Prefer range-based for loops: for (const auto& item : container)
- Use std:: prefix unless 'using namespace std' is in <PREFIX>
- Match existing naming convention (camelCase, snake_case, or PascalCase)"""
```

---

### Phân tích C++ Guidelines

#### Flexible Indentation

```python
- Match existing indentation (usually 2 or 4 spaces, or tabs)
```

**C++ varies:**
```cpp
// 2 spaces (Google style):
int foo() {
  return 42;
}

// 4 spaces:
int foo() {
    return 42;
}

// Tabs (some projects):
int foo() {
	return 42;
}
```

**Match what's in PREFIX!**

---

#### Semicolons

```python
- Include semicolons and proper braces {} placement
```

**Required in C++:**
```cpp
int x = 10;  // ← Semicolon required!

int foo() {  // ← Braces
    return x;
}
```

---

#### Auto Keyword

```python
- Use 'auto' for complex types when appropriate
```

**Example:**
```cpp
// Complex type:
std::map<std::string, std::vector<int>>::iterator it = myMap.begin();

// Simplified with auto:
auto it = myMap.begin();  ✅
```

---

#### Range-Based For Loops

```python
- Prefer range-based for loops: for (const auto& item : container)
```

**Modern C++:**
```cpp
// Good (range-based):
for (const auto& item : container) {
    std::cout << item << std::endl;
}

// Avoid (index-based when not needed):
for (size_t i = 0; i < container.size(); i++) {
    std::cout << container[i] << std::endl;
}
```

---

#### Namespace Prefix

```python
- Use std:: prefix unless 'using namespace std' is in <PREFIX>
```

**Check PREFIX:**

**PREFIX has `using namespace std`:**
```cpp
using namespace std;

int main() {
    cout << "Hello";  // ✅ No std:: needed
```

**PREFIX doesn't:**
```cpp
int main() {
    std::cout << "Hello";  // ✅ std:: required
```

---

### Step 5: Add User Personalization

```python
    # Add user personalization
    style_hints = f"\nUSER PREFERENCES: {user_style_hints}" if user_style_hints else ""
```

**Conditional injection:**

**With hints:**
```python
user_style_hints = "Use type hints. Prefer list comprehensions."
style_hints = "\nUSER PREFERENCES: Use type hints. Prefer list comprehensions."
```

**Without hints:**
```python
user_style_hints = ""
style_hints = ""  # Empty
```

---

### Step 6: Few-Shot Examples (C++)

```python
    # Few-shot examples with proper FIM format
    if req.language in ["cpp", "c++", "c"]:
        examples = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE 1 - Simple function completion:
<PREFIX>
int add(int a, int b) {
    
</PREFIX>
<SUFFIX>
}

int main() {
</SUFFIX>
<FILL>return a + b;</FILL>
```

---

### Phân tích Few-Shot Learning

#### What is Few-Shot?

**Definition:** Give LLM examples before actual task

**Benefits:**
1. Shows expected format
2. Demonstrates correct behavior
3. Improves accuracy dramatically

**Studies show:**
- 0-shot (no examples): ~60% accuracy
- Few-shot (3-5 examples): ~85% accuracy
- GitHub Copilot uses this technique!

---

#### Example 1 Breakdown

**Structure:**
```
<PREFIX> ... </PREFIX>  ← Code before cursor
<SUFFIX> ... </SUFFIX>  ← Code after cursor  
<FILL> ... </FILL>      ← What to generate
```

**Teaching:**
```cpp
<PREFIX>
int add(int a, int b) {
    ← Cursor here (empty space)
</PREFIX>
<SUFFIX>
}  ← Function closes

int main() {
</SUFFIX>
<FILL>return a + b;</FILL>  ← Correct completion!
```

**LLM learns:**
- Don't repeat `int add(...)` (it's in PREFIX)
- Don't repeat `}` (it's in SUFFIX)
- Generate just the function body: `return a + b;`

---

#### Example 2: Indentation

```cpp
EXAMPLE 2 - Loop with proper indentation:
<PREFIX>
void printArray(int arr[], int size) {
    for (int i = 0; i < size; i++) {
        ← 8 spaces indent (nested)
</PREFIX>
<SUFFIX>
    }  ← 4 spaces (close for)
}  ← 0 spaces (close function)
</SUFFIX>
<FILL>std::cout << arr[i] << " ";</FILL>
```

**Teaching:**
- Maintain 8-space indent (2 levels deep)
- Use `std::` prefix
- Access array with `arr[i]`

---

#### Example 3: Class Method

```cpp
EXAMPLE 3 - Class method:
<PREFIX>
class Calculator {
public:
    int multiply(int a, int b) {
        ← 8 spaces indent
</PREFIX>
<SUFFIX>
    }  ← Close method
};  ← Close class
</SUFFIX>
<FILL>return a * b;</FILL>
```

**Teaching:**
- Method completion inside class
- Simple return statement
- Match indentation

---

### Step 7: Few-Shot Examples (Python)

```python
    else:  # Python
        examples = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE 1 - Simple function completion:
<PREFIX>
def calculate_sum(numbers):
    
</PREFIX>
<SUFFIX>

result = calculate_sum([1, 2, 3])
</SUFFIX>
<FILL>if not numbers:
        return 0
    return sum(numbers)</FILL>
```

---

### Phân tích Python Examples

#### Example 1: Multi-line Completion

**Teaching:**
```python
<FILL>if not numbers:
        return 0
    return sum(numbers)</FILL>
```

**Multiple lines with correct indentation:**
- Line 1: `if not numbers:` (4 spaces)
- Line 2: `return 0` (8 spaces - nested)
- Line 3: `return sum(numbers)` (4 spaces)

**LLM learns:**
- Can generate multiple lines
- Must maintain indentation levels
- Include error handling (`if not numbers`)

---

#### Example 2: Inline Completion

```python
EXAMPLE 2 - Inline completion:
<PREFIX>
def is_even(n):
    return 
</PREFIX>
<SUFFIX>

def is_odd(n):
</SUFFIX>
<FILL>n % 2 == 0</FILL>
```

**Teaching:**
- Single-line completion
- Expression only (no `return` keyword - already in PREFIX)
- Concise solution

---

#### Example 3: List Comprehension

```python
EXAMPLE 3 - List comprehension:
<PREFIX>
names = ['alice', 'bob', 'charlie']
uppercase_names = [
</PREFIX>
<SUFFIX>
]
print(uppercase_names)
</SUFFIX>
<FILL>name.upper() for name in names</FILL>
```

**Teaching:**
- List comprehension syntax
- Variable name (`name`) matches context (`names`)
- Idiomatic Python (not a loop)

---

#### Example 4: Multi-line with Class

```python
EXAMPLE 4 - Multi-line with proper indent:
<PREFIX>
class UserManager:
    def validate_user(self, user_id):
        
</PREFIX>
<SUFFIX>
        return is_valid
    
    def delete_user(self, user_id):
</SUFFIX>
<FILL>if not user_id:
            return False
        user = self.db.get_user(user_id)
        is_valid = user is not None and user.active</FILL>
```

**Teaching:**
- Class method completion
- Multiple lines with varying indentation:
  - Line 1: 8 spaces (`if not user_id:`)
  - Line 2: 12 spaces (`return False`)
  - Line 3: 8 spaces (`user = ...`)
  - Line 4: 8 spaces (`is_valid = ...`)
- Use of `self` in methods
- Complex logic with multiple statements

---

### Step 8: Build Final Prompt

```python
    # Build final prompt with FIM structure
    prompt = f"""{system_msg}
{lang_rules}{style_hints}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEARN FROM THESE EXAMPLES:
{examples}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOW COMPLETE THIS CODE:

<PREFIX>
{req.prefix}
</PREFIX>

<SUFFIX>
{req.suffix}
</SUFFIX>

<FILL>"""
    
    return prompt
```

---

### Phân tích Final Prompt Structure

**Complete prompt sections:**

1. **System Message** (role + rules)
2. **Language Guidelines** (Python/C++ specific)
3. **User Style Hints** (personalization)
4. **Separator** (`━━━━━━...`)
5. **Examples Header** (`LEARN FROM THESE EXAMPLES:`)
6. **Few-Shot Examples** (3-4 examples)
7. **Separator** (`━━━━━━...`)
8. **Actual Task Header** (`NOW COMPLETE THIS CODE:`)
9. **Actual PREFIX/SUFFIX** (user's code)
10. **FILL Marker** (where LLM generates)

---

### Example Complete Prompt

```
You are an expert python code completion engine. Your task is to complete code at the <FILL> position.

CRITICAL RULES:
1. Output ONLY the missing code - NO explanations, NO markdown, NO backticks
2. Match the existing code style EXACTLY (indentation, naming, patterns)
...

Python Guidelines:
- Use 4 spaces for indentation (never tabs)
- Follow PEP 8 naming: snake_case for functions/variables
...

USER PREFERENCES: Use type hints. Prefer list comprehensions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEARN FROM THESE EXAMPLES:

EXAMPLE 1 - Simple function completion:
<PREFIX>
def calculate_sum(numbers):
    
</PREFIX>
<SUFFIX>

result = calculate_sum([1, 2, 3])
</SUFFIX>
<FILL>if not numbers:
        return 0
    return sum(numbers)</FILL>

... (more examples) ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOW COMPLETE THIS CODE:

<PREFIX>
def fibonacci(n):
    
</PREFIX>

<SUFFIX>

result = fibonacci(10)
</SUFFIX>

<FILL>
```

**LLM will generate:**
```python
if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

---

## 🌐 Function: `call_groq_completion()`

### Purpose
**Call Groq API** với retry logic và error handling

### Function Signature

```python
def call_groq_completion(
    prompt: str, 
    max_tokens: int, 
    temperature: float,
    stop: Optional[list[str]] = None
) -> str:
    """
    Call Groq API for code completion.
    Returns the raw completion text.
    """
```

---

### Step 1: Validate API Key

```python
    if not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY not configured"
        )
```

**Check before calling API:**
- Prevents wasted API calls
- Returns clear error message
- 500 = server configuration issue

---

### Step 2: Prepare Request

```python
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
```

---

#### Groq API Endpoint

```python
url = "https://api.groq.com/openai/v1/chat/completions"
```

**OpenAI-compatible API:**
- Groq uses same format as OpenAI
- Easy to switch between providers
- Standard `/chat/completions` endpoint

---

#### Headers

```python
headers = {
    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
    "Content-Type": "application/json"
}
```

**Authorization:**
```
Bearer gsk_abc123xyz...
```

**Standard OAuth 2.0 format**

---

### Step 3: Limit Stop Sequences

```python
    # Groq uses OpenAI-compatible API
    # Limit stop sequences to max 4 (Groq requirement)
    stop_sequences = (stop or [])[:4] if stop else []
```

---

#### Groq Limitation

**Groq API allows maximum 4 stop sequences**

**Slice to first 4:**
```python
stop = ["\ndef ", "\nclass ", "\nif ", "\n#", "```"]  # 5 items
stop_sequences = stop[:4]
# → ["\ndef ", "\nclass ", "\nif ", "\n#"]  # Only 4
```

**Empty case:**
```python
stop = None
stop_sequences = []  # Empty list
```

---

### Step 4: Build Request Body

```python
    body = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a code completion assistant. Return only the code that should appear at the cursor, without any markdown formatting or explanations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stop": stop_sequences,
        "stream": False
    }
```

---

### Phân tích Request Body

#### `"model"`

```python
"model": settings.GROQ_MODEL
```

**Example:**
```python
# From config:
GROQ_MODEL = "llama-3.3-70b-versatile"

# In request:
"model": "llama-3.3-70b-versatile"
```

**Available models:**
- `llama-3.3-70b-versatile` (recommended)
- `mixtral-8x7b-32768`
- `deepseek-r1-distill-llama-70b`

---

#### `"messages"` - Chat Format

```python
"messages": [
    {
        "role": "system",
        "content": "You are a code completion assistant..."
    },
    {
        "role": "user",
        "content": prompt  # Our FIM prompt
    }
]
```

**OpenAI chat format:**
- `system`: Sets behavior/persona
- `user`: The actual prompt
- LLM responds as `assistant`

---

#### System Message

```python
"You are a code completion assistant. Return only the code that should appear at the cursor, without any markdown formatting or explanations."
```

**Reinforces rules:**
- Code only (no explanations)
- No markdown (no ``` fences)
- Position-aware ("at the cursor")

---

#### User Message

```python
"content": prompt
```

**This is our FIM prompt:**
- System message + guidelines + examples + actual task
- 500-2000 tokens long (detailed!)

---

#### Other Parameters

```python
"max_tokens": max_tokens,     # 128 (default)
"temperature": temperature,   # 0.2 (default)
"stop": stop_sequences,       # ["\ndef ", ...]
"stream": False               # Non-streaming (get full response)
```

---

### Step 5: Make API Call

```python
    try:
        logger.info(f"Calling Groq API with model {settings.GROQ_MODEL}")
        resp = requests.post(
            url, 
            headers=headers, 
            json=body, 
            timeout=settings.TIMEOUT_SECONDS
        )
```

---

#### Logging

```python
logger.info(f"Calling Groq API with model {settings.GROQ_MODEL}")
```

**Output:**
```
[INFO] Calling Groq API with model llama-3.3-70b-versatile
```

---

#### HTTP POST

```python
resp = requests.post(
    url,
    headers=headers,
    json=body,
    timeout=settings.TIMEOUT_SECONDS
)
```

**`json=body`:**
- Automatic JSON serialization
- Sets `Content-Type: application/json`

**`timeout=settings.TIMEOUT_SECONDS`:**
- Default: 30 seconds
- Prevents hanging forever
- Raises `requests.exceptions.Timeout` if exceeded

---

### Step 6: Handle HTTP Errors

```python
        if resp.status_code >= 400:
            error_detail = resp.text[:500]
            logger.error(f"Groq API error {resp.status_code}: {error_detail}")
            raise HTTPException(
                status_code=502,
                detail={"groq_error": error_detail}
            )
```

---

#### Check Status Code

```python
if resp.status_code >= 400:
```

**Error codes:**
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (invalid API key)
- `429`: Rate Limit Exceeded
- `500`: Groq Internal Server Error
- `503`: Service Unavailable

---

#### Truncate Error

```python
error_detail = resp.text[:500]
```

**Why truncate?**
- Error responses can be long
- Prevent response bloat
- First 500 chars usually sufficient

---

#### Return 502 Bad Gateway

```python
raise HTTPException(
    status_code=502,
    detail={"groq_error": error_detail}
)
```

**502 = Upstream service error:**
- Our server OK
- External service (Groq) failed
- Appropriate status code

---

### Step 7: Parse Response

```python
        data = resp.json()
        completion = data["choices"][0]["message"]["content"]
        
        logger.info(f"Groq completion received: {len(completion)} chars")
        return completion
```

---

#### Response Format

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1699704225,
  "model": "llama-3.3-70b-versatile",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "return a + b"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 250,
    "completion_tokens": 10,
    "total_tokens": 260
  }
}
```

---

#### Extract Completion

```python
completion = data["choices"][0]["message"]["content"]
```

**Navigation:**
```python
data["choices"]           # List of choices
    [0]                   # First choice (usually only 1)
        ["message"]       # Message object
            ["content"]   # Actual text: "return a + b"
```

---

#### Log Success

```python
logger.info(f"Groq completion received: {len(completion)} chars")
```

**Output:**
```
[INFO] Groq completion received: 15 chars
```

**Useful for:**
- Monitoring completion lengths
- Debugging
- Performance tracking

---

### Step 8: Handle Network Errors

```python
    except requests.exceptions.RequestException as e:
        logger.exception("Network error calling Groq API")
        raise HTTPException(
            status_code=502,
            detail={"groq_error": f"Network error: {str(e)}"}
        )
```

**RequestException catches:**
- `Timeout`: Request took too long
- `ConnectionError`: Can't reach server
- `HTTPError`: HTTP-level errors
- All `requests` library errors

---

### Step 9: Handle Parse Errors

```python
    except KeyError as e:
        logger.exception("Unexpected response format from Groq")
        raise HTTPException(
            status_code=502,
            detail={"groq_error": f"Invalid response format: {str(e)}"}
        )
```

**KeyError when:**
```python
# Missing fields:
data["choices"]  # KeyError if no "choices" key

# Structure changed:
data["choices"][0]["message"]["content"]
# KeyError if any part missing
```

**Protects against:**
- API changes
- Malformed responses
- Unexpected formats

---

## 🆔 Function: `new_request_id()`

### Purpose
**Generate unique request ID** for tracking

### Code

```python
def new_request_id() -> str:
    """Generate unique request ID."""
    return str(uuid.uuid4())[:8]
```

---

### Phân tích

#### UUID4

```python
uuid.uuid4()
```

**Generates:**
```
UUID('550e8400-e29b-41d4-a716-446655440000')
```

**Random UUID (version 4)**

---

#### Convert to String

```python
str(uuid.uuid4())
```

**Result:**
```
"550e8400-e29b-41d4-a716-446655440000"
```

**36 characters (with dashes)**

---

#### Take First 8

```python
str(uuid.uuid4())[:8]
```

**Result:**
```
"550e8400"
```

**Short ID:**
- 8 hex characters
- Still very unique (~4 billion combinations)
- Easy to read/type
- Good for logs

**Example usage:**
```python
req_id = new_request_id()
# → "a3f5b2c7"

logger.info(f"[{req_id}] Processing completion")
# → [INFO] [a3f5b2c7] Processing completion
```

---

## 💡 Key Points cho thuyết trình

### 1. FIM (Fill-In-the-Middle) Prompting

**Why FIM?**

**Traditional (Left-to-Right):**
```
Prompt: "def add(a, b):"
Model generates: "    return a + b\n\ndef subtract..."
Problem: Keeps generating unrelated code!
```

**FIM (our approach):**
```
<PREFIX>def add(a, b):</PREFIX>
<SUFFIX>}\n\nprint('test')</SUFFIX>
Model generates ONLY what's needed between them ✅
```

**Advantages:**
- Precise completions
- Context-aware (knows what comes after)
- Stops at logical boundaries

---

### 2. Few-Shot Learning Impact

**Accuracy comparison:**

| Approach | Accuracy | Example |
|----------|----------|---------|
| **0-shot** (no examples) | ~60% | "Complete this code" |
| **Few-shot** (3-5 examples) | ~85% | "Learn from examples, then complete" |
| **Fine-tuned** | ~90%+ | Trained on similar data |

**We use few-shot** because:
- Don't need expensive fine-tuning
- Can update examples easily
- Portable across models

---

### 3. Prompt Engineering Best Practices

**Our prompt structure:**
1. ✅ Clear role definition ("expert code completion engine")
2. ✅ Explicit rules ("Output ONLY code, NO markdown")
3. ✅ Language-specific guidelines (PEP 8, etc.)
4. ✅ Few-shot examples (3-4 per language)
5. ✅ User personalization (style hints)
6. ✅ Clear task formatting (<PREFIX>, <SUFFIX>, <FILL>)

**Why this works:**
- LLMs need structure (not free-form)
- Examples demonstrate format
- Rules prevent common mistakes
- Personalization improves acceptance

---

### 4. Error Handling Strategy

**Three layers:**

**Layer 1: Configuration**
```python
if not settings.GROQ_API_KEY:
    raise HTTPException(500, "API key not configured")
```

**Layer 2: HTTP Errors**
```python
if resp.status_code >= 400:
    raise HTTPException(502, {"groq_error": error_detail})
```

**Layer 3: Network Errors**
```python
except requests.exceptions.RequestException:
    raise HTTPException(502, "Network error")
```

**Layer 4: Parse Errors**
```python
except KeyError:
    raise HTTPException(502, "Invalid response format")
```

**All errors converted to HTTPException** → Client gets proper HTTP response

---

### 5. Groq vs Ollama

**Why switched from Ollama to Groq?**

| Aspect | Ollama (old) | Groq (new) |
|--------|--------------|------------|
| **Speed** | ~2-5s | ~0.2-0.5s (10x faster!) |
| **Setup** | Local installation | Cloud API (no setup) |
| **Cost** | Free (local) | Free tier (10K requests/day) |
| **Reliability** | Depends on hardware | 99.9% uptime |
| **Models** | Limited selection | Latest models (Llama 3.3, etc.) |

**Decision: Groq for production** ✅

---

## 🧪 Test Cases

### Test 1: Build prompt (Python)

```python
from app.schemas.completion import CompleteRequest

req = CompleteRequest(
    prefix="def add(a, b):\n    ",
    suffix="\n\nprint('test')",
    language="python",
    max_tokens=100,
    temperature=0.2
)

prompt = build_prompt(req)

assert "expert python code completion engine" in prompt.lower()
assert "<PREFIX>" in prompt
assert "def add(a, b):" in prompt
assert "<SUFFIX>" in prompt
assert "print('test')" in prompt
assert "<FILL>" in prompt
assert "PEP 8" in prompt
```

---

### Test 2: Build prompt with user hints

```python
req = CompleteRequest(
    prefix="def add(",
    language="python"
)

user_hints = "Use type hints. Prefer list comprehensions."
prompt = build_prompt(req, user_hints)

assert "USER PREFERENCES" in prompt
assert "Use type hints" in prompt
assert "list comprehensions" in prompt
```

---

### Test 3: Call Groq API (mocked)

```python
from unittest.mock import patch, Mock

mock_response = Mock()
mock_response.status_code = 200
mock_response.json.return_value = {
    "choices": [
        {
            "message": {
                "content": "return a + b"
            }
        }
    ]
}

with patch('requests.post', return_value=mock_response):
    completion = call_groq_completion(
        prompt="test prompt",
        max_tokens=100,
        temperature=0.2,
        stop=["\ndef "]
    )
    
    assert completion == "return a + b"
```

---

### Test 4: Handle API error

```python
mock_response = Mock()
mock_response.status_code = 429  # Rate limit
mock_response.text = "Rate limit exceeded"

with patch('requests.post', return_value=mock_response):
    with pytest.raises(HTTPException) as exc:
        call_groq_completion("test", 100, 0.2)
    
    assert exc.value.status_code == 502
    assert "groq_error" in exc.value.detail
```

---

### Test 5: Handle network error

```python
import requests

with patch('requests.post', side_effect=requests.exceptions.Timeout):
    with pytest.raises(HTTPException) as exc:
        call_groq_completion("test", 100, 0.2)
    
    assert exc.value.status_code == 502
    assert "Network error" in str(exc.value.detail)
```

---

### Test 6: Generate request ID

```python
req_id1 = new_request_id()
req_id2 = new_request_id()

assert len(req_id1) == 8
assert len(req_id2) == 8
assert req_id1 != req_id2  # Different IDs
assert all(c in "0123456789abcdef" for c in req_id1)  # Hex characters
```

---

**File này hoàn tất!** 🎉 Đây là file PHỨC TẠP NHẤT và QUAN TRỌNG NHẤT của project!

**Tiếp theo:** `user_profiling.py` và `ollama.py`. Tiếp tục không? 🚀

