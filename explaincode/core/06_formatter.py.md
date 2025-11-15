# Giải thích chi tiết: `server/app/core/formatter.py`

## 📋 Mục đích của file

File này **auto-format code completions** để đảm bảo code tuân theo style guides:
- **Python:** PEP 8 (via `black` hoặc `autopep8`)
- **C++:** Google/LLVM style (via `clang-format`)
- **Fallback:** Lightweight normalization nếu formatter không có

---

## 🔍 Module Docstring & Imports

```python
"""
Code formatter integration for auto-formatting completions.
Supports black (Python), prettier (JavaScript/TypeScript), and clang-format (C++).
"""
import subprocess
import tempfile
import os
from typing import Optional, Literal
```

**Giải thích imports:**

### `subprocess`
- Chạy external commands (black, clang-format) as subprocesses
- Capture stdout/stderr

### `tempfile`
- Tạo temporary files (cần cho `black` - format file)

### `os`
- File operations (delete temp files)

### `Optional, Literal`
- Type hints:
  - `Optional[str]`: `str` hoặc `None`
  - `Literal["black", "autopep8"]`: Chỉ accept specific strings

---

## 🐍 Function 1: `format_python_code()`

### Signature

```python
def format_python_code(code: str, line_length: int = 88) -> tuple[str, Optional[str]]:
    """
    Format Python code using black.
    Returns (formatted_code, error_message).
    If formatting fails, returns original code with error message.
    """
```

**Return type: `tuple[str, Optional[str]]`**
- Tuple with 2 elements:
  1. `str`: Formatted code (hoặc original nếu fail)
  2. `Optional[str]`: Error message (None nếu thành công)

**Pattern: Never throw exceptions**
- Luôn return code (formatted hoặc original)
- Caller decide xử lý error thế nào

---

### Step 1: Create temp file

```python
    try:
        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
```

**Tại sao cần temp file?**

**Black chỉ format files, không accept stdin:**
```bash
# Black CLI:
black file.py       ✅ Works
echo "code" | black ❌ Doesn't work
```

**tempfile.NamedTemporaryFile:**
```python
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
```

**Parameters:**
- `mode='w'`: Write text mode
- `suffix='.py'`: File extension (black check này)
- `delete=False`: **KHÔNG** tự động xóa khi close
  - Lý do: Ta cần đọc lại file sau khi black format
  - Sẽ xóa manual bằng `os.unlink()`

**`f.name`:**
- Full path của temp file
- VD: `/tmp/tmpXYZ123.py`

---

### Step 2: Run black

```python
        try:
            # Run black on the temp file
            result = subprocess.run(
                ['black', '--quiet', '--line-length', str(line_length), temp_path],
                capture_output=True,
                text=True,
                timeout=5
            )
```

**Phân tích subprocess.run():**

#### Command: `['black', '--quiet', '--line-length', '88', '/tmp/tmpXYZ.py']`

**Equivalent shell command:**
```bash
black --quiet --line-length 88 /tmp/tmpXYZ.py
```

**Arguments:**
- `--quiet`: Không print progress messages
- `--line-length 88`: Max line length (PEP 8 default)
- `temp_path`: File path to format

---

#### `capture_output=True`

**Ý nghĩa:**
- Capture stdout và stderr
- Access via `result.stdout`, `result.stderr`

**Without capture_output:**
```python
subprocess.run(['black', ...])
# Output prints to console (không capture được)
```

**With capture_output:**
```python
result = subprocess.run(['black', ...], capture_output=True)
print(result.stdout)  # Có thể access
```

---

#### `text=True`

**Ý nghĩa:**
- Return stdout/stderr as strings (not bytes)

**Comparison:**
```python
# text=False (default):
result.stdout = b"All done!"  # bytes

# text=True:
result.stdout = "All done!"   # str
```

---

#### `timeout=5`

**Ý nghĩa:**
- Kill process nếu chạy > 5 giây
- Raise `subprocess.TimeoutExpired`

**Tại sao cần timeout?**
- Tránh black "treo" (rare case)
- LLM completion nên format nhanh (<1s)

---

### Step 3: Check result & read formatted code

```python
            if result.returncode == 0:
                # Read formatted code
                with open(temp_path, 'r') as f:
                    formatted = f.read()
                return formatted, None
            else:
                error = result.stderr or "Black formatting failed"
                return code, error
```

**`result.returncode`:**
- `0`: Success
- Non-zero: Error

**Success path:**
```python
# Black đã modify temp file in-place
# Đọc file để lấy formatted code
with open(temp_path, 'r') as f:
    formatted = f.read()
return formatted, None  # (formatted code, no error)
```

**Error path:**
```python
error = result.stderr or "Black formatting failed"
return code, error  # (original code, error message)
```

---

### Step 4: Cleanup

```python
        finally:
            # Clean up temp file
            os.unlink(temp_path)
```

**`finally` block:**
- Always executes (success hoặc exception)
- Đảm bảo temp file bị xóa

**`os.unlink()`:**
- Delete file
- Equivalent to `os.remove()`

---

### Exception handling

```python
    except FileNotFoundError:
        return code, "black not installed (pip install black)"
    except subprocess.TimeoutExpired:
        return code, "Black formatting timeout"
    except Exception as e:
        return code, f"Formatting error: {str(e)}"
```

**FileNotFoundError:**
- `black` command không tồn tại
- User chưa install: `pip install black`

**TimeoutExpired:**
- Black chạy > 5 giây

**Generic Exception:**
- Catch-all cho bất kỳ error nào khác
- VD: Permission denied, disk full, etc.

---

### Complete example

```python
# Input
code = """def add(a,b):
  return a+b"""

# Call
formatted, error = format_python_code(code)

# formatted:
"""def add(a, b):
    return a + b
"""

# error: None ✅
```

---

## 🔧 Function 2: `format_with_autopep8()`

### Tại sao cần autopep8 nếu đã có black?

**Black vs autopep8:**

| Aspect | Black | autopep8 |
|--------|-------|----------|
| **Style** | Opinionated, strict | Flexible, PEP 8 only |
| **Changes** | Aggressive (reformat all) | Conservative (fix violations) |
| **Config** | Minimal | Highly configurable |
| **Speed** | Fast | Faster |

**Use case:** Fallback nếu black không có hoặc fail

---

### Code

```python
def format_with_autopep8(code: str, max_line_length: int = 88) -> tuple[str, Optional[str]]:
    """
    Format Python code using autopep8 (less aggressive than black).
    Returns (formatted_code, error_message).
    """
    try:
        result = subprocess.run(
            ['autopep8', '--max-line-length', str(max_line_length), '-'],
            input=code,
            capture_output=True,
            text=True,
            timeout=5
        )
```

**Key difference: `input=code` instead of temp file**

**autopep8 accepts stdin:**
```bash
echo "def foo( x ):return x" | autopep8 -
# Output: def foo(x): return x
```

**`'-'` argument:**
- Means "read from stdin"
- Equivalent to shell `|`

**No temp file needed! Simpler than black.**

---

### Rest of function (similar to black)

```python
        if result.returncode == 0:
            return result.stdout, None
        else:
            return code, result.stderr or "autopep8 failed"
            
    except FileNotFoundError:
        return code, "autopep8 not installed (pip install autopep8)"
    except subprocess.TimeoutExpired:
        return code, "autopep8 timeout"
    except Exception as e:
        return code, f"Formatting error: {str(e)}"
```

---

## 📝 Function 3: `normalize_python_code()`

### Mục đích
**Lightweight formatting** khi không có black/autopep8

### Code phân tích

```python
def normalize_python_code(code: str) -> str:
    """
    Lightweight normalization for Python code when a proper formatter
    is not available or fails.

    - Convert tabs to 4 spaces
    - Strip trailing whitespace
    - Collapse multiple blank lines to a single blank line
    - Ensure consistent newline endings (\n)
    - Remove leading/trailing blank lines
    """
```

---

### Step 1: Normalize newlines

```python
    if not code:
        return code

    # Normalize newlines
    text = code.replace('\r\n', '\n').replace('\r', '\n')
```

**Tại sao cần?**

**Different OS line endings:**
- Unix/Mac: `\n` (LF)
- Windows: `\r\n` (CRLF)
- Old Mac: `\r` (CR)

**Normalize all to `\n`:**
```python
text = "line1\r\nline2\rline3\n"
text = text.replace('\r\n', '\n')  # → "line1\nline2\rline3\n"
text = text.replace('\r', '\n')    # → "line1\nline2\nline3\n"
```

**Order matters!**
- Phải replace `\r\n` trước `\r`
- Nếu không: `\r\n` → `\n\n` (double newline)

---

### Step 2: Tabs to spaces

```python
    # Replace tabs with 4 spaces
    text = text.replace('\t', ' ' * 4)
```

**PEP 8:** Python prefer spaces over tabs (4 spaces per indent level)

**Example:**
```python
text = "def foo():\n\treturn 42"
text = text.replace('\t', '    ')
# → "def foo():\n    return 42"
```

---

### Step 3: Strip trailing whitespace

```python
    # Strip trailing spaces on each line
    lines = [ln.rstrip() for ln in text.split('\n')]
```

**`.rstrip()`:** Remove whitespace from right side

**Example:**
```python
text = "def foo():    \n    return 42  "
lines = text.split('\n')
# → ["def foo():    ", "    return 42  "]

lines = [ln.rstrip() for ln in lines]
# → ["def foo():", "    return 42"]
```

**Tại sao cần?**
- Trailing spaces vô nghĩa
- Git diff hiển thị nhiễu
- Some editors auto-remove anyway

---

### Step 4: Collapse multiple blank lines

```python
    # Collapse multiple blank lines
    new_lines: list[str] = []
    blank = False
    for ln in lines:
        if ln == "":
            if not blank:
                new_lines.append("")
            blank = True
        else:
            new_lines.append(ln)
            blank = False
```

**Logic:**

**State machine với flag `blank`:**
```
blank = False (initially)

For each line:
    If line is empty:
        If not blank:  (first blank line)
            Append ""
            blank = True
        Else:  (consecutive blank line)
            Skip (don't append)
    Else:  (non-empty line)
        Append line
        blank = False
```

**Example:**
```python
lines = ["def foo():", "", "", "", "    pass"]

# Processing:
# Line 0: "def foo()" → Append, blank=False
# Line 1: "" → Append (first blank), blank=True
# Line 2: "" → Skip (blank=True already)
# Line 3: "" → Skip
# Line 4: "    pass" → Append, blank=False

new_lines = ["def foo():", "", "    pass"]
```

**PEP 8:** Maximum 2 blank lines between functions, 1 within functions

---

### Step 5: Remove leading/trailing blank lines

```python
    # Remove leading/trailing blank lines
    while new_lines and new_lines[0] == "":
        new_lines.pop(0)
    while new_lines and new_lines[-1] == "":
        new_lines.pop()
```

**Example:**
```python
new_lines = ["", "", "def foo():", "    pass", "", ""]

# Remove leading:
while new_lines[0] == "":
    new_lines.pop(0)
# → ["def foo():", "    pass", "", ""]

# Remove trailing:
while new_lines[-1] == "":
    new_lines.pop()
# → ["def foo():", "    pass"]
```

---

### Return

```python
    return "\n".join(new_lines)
```

**Join lines back với `\n`:**
```python
new_lines = ["def foo():", "    pass"]
result = "\n".join(new_lines)
# → "def foo():\n    pass"
```

---

## 🔨 Function 4: `format_cpp_code()`

### Code

```python
def format_cpp_code(code: str) -> tuple[str, Optional[str]]:
    """
    Format C++ code using clang-format.
    Returns (formatted_code, error_message).
    If formatting fails, returns original code with error message.
    """
    try:
        result = subprocess.run(
            ['clang-format', '--style=LLVM'],
            input=code,
            capture_output=True,
            text=True,
            timeout=5
        )
```

**Command: `clang-format --style=LLVM`**

**`--style=LLVM`:**
- LLVM coding style (used by LLVM project)
- Alternative styles: `Google`, `Chromium`, `Mozilla`, `WebKit`

**Example LLVM style:**
```cpp
// Input:
int main(){std::cout<<"Hello"<<std::endl;return 0;}

// Output (LLVM style):
int main() {
  std::cout << "Hello" << std::endl;
  return 0;
}
```

**clang-format accepts stdin:**
```bash
echo "int main(){return 0;}" | clang-format --style=LLVM
```

---

### Rest (similar to autopep8)

```python
        if result.returncode == 0:
            return result.stdout, None
        else:
            return code, result.stderr or "clang-format failed"
            
    except FileNotFoundError:
        return code, "clang-format not installed"
    except subprocess.TimeoutExpired:
        return code, "clang-format timeout"
    except Exception as e:
        return code, f"Formatting error: {str(e)}"
```

---

## 🔧 Function 5: `normalize_cpp_code()`

### Code

```python
def normalize_cpp_code(code: str) -> str:
    """
    Lightweight normalization for C++ code when clang-format is not available.
    
    - Convert tabs to 2 spaces (C++ convention)
    - Strip trailing whitespace
    - Normalize newlines
    """
    if not code:
        return code
    
    # Normalize newlines
    text = code.replace('\r\n', '\n').replace('\r', '\n')
    
    # Replace tabs with 2 spaces (C++ convention)
    text = text.replace('\t', '  ')
```

**Key difference: 2 spaces thay vì 4 (C++ convention)**

**Python:** 4 spaces per indent
**C++:** 2 spaces per indent (Google style, LLVM style)

---

### Rest (same logic as Python normalize)

```python
    # Strip trailing spaces on each line
    lines = [ln.rstrip() for ln in text.split('\n')]
    
    # Remove leading/trailing blank lines
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    
    return "\n".join(lines)
```

**Note:** Không collapse multiple blank lines (C++ style cho phép nhiều blank lines)

---

## 🎯 Function 6: `format_code()` - Main entry point

### Signature

```python
def format_code(
    code: str,
    language: Literal["python", "javascript", "typescript", "cpp", "c++", "c", ""] = "python",
    formatter: Literal["black", "autopep8", "prettier", "clang-format", "auto"] = "auto"
) -> tuple[str, Optional[str]]:
```

**Type hints với Literal:**
- `language`: Chỉ accept specific strings
- `formatter`: "auto" (recommended) hoặc specify formatter

---

### Auto-select formatter

```python
    if not code.strip():
        return code, None
    
    # Auto-select formatter based on language
    if formatter == "auto":
        if language == "python":
            formatter = "black"
        elif language in ("javascript", "typescript"):
            formatter = "prettier"
        elif language in ("cpp", "c++", "c"):
            formatter = "clang-format"
        else:
            return code, None  # No formatter for this language
```

**Mapping:**
```
python       → black
javascript   → prettier
typescript   → prettier
cpp/c++/c    → clang-format
other        → No formatting
```

---

### Apply formatter

```python
    # Apply formatter
    if formatter == "black":
        return format_python_code(code)
    elif formatter == "autopep8":
        return format_with_autopep8(code)
    elif formatter == "clang-format":
        return format_cpp_code(code)
    elif formatter == "prettier":
        return code, "prettier not yet implemented"
    else:
        return code, f"Unknown formatter: {formatter}"
```

**Delegation pattern:**
- Main function chỉ routing
- Actual logic ở specific formatters

---

## ✅ Function 7: `should_format()`

### Mục đích
Decide có nên format hay không (skip short/trivial completions)

### Code

```python
def should_format(code: str, language: str) -> bool:
    """
    Decide if code should be formatted.
    Skip formatting for very short completions or non-code.
    """
    # Skip empty or very short code
    if len(code.strip()) < 10:
        return False
    
    # Skip if not a supported language
    if language not in ("python", "javascript", "typescript", "cpp", "c++", "c"):
        return False
    
    # Skip if it's just a single expression
    if '\n' not in code and len(code) < 50:
        return False
    
    return True
```

**Logic:**

### Check 1: Too short

```python
if len(code.strip()) < 10:
    return False
```

**Examples skip:**
```python
"return x"  # 8 chars → Skip
"pass"      # 4 chars → Skip
```

**Tại sao skip?**
- Formatting overhead không đáng
- Short code usually already formatted

---

### Check 2: Unsupported language

```python
if language not in ("python", "javascript", "typescript", "cpp", "c++", "c"):
    return False
```

**Skip nếu language = "java", "rust", etc.**

---

### Check 3: Single expression

```python
if '\n' not in code and len(code) < 50:
    return False
```

**Examples skip:**
```python
"a + b"           # No newline, short → Skip
"user.get_name()" # No newline, short → Skip
```

**Format nếu:**
```python
"def add(a, b):\n    return a + b"  # Multi-line → Format ✅
```

---

## 🧪 Main block (testing)

```python
if __name__ == "__main__":
    test_code = """
def fibonacci(n):
    if n<=1:return n
    return fibonacci(n-1)+fibonacci(n-2)
"""
    
    print("Original code:")
    print(test_code)
    print("\nFormatted with black:")
    formatted, error = format_python_code(test_code.strip())
    if error:
        print(f"Error: {error}")
    else:
        print(formatted)
```

**Run:**
```bash
python server/app/core/formatter.py

# Output:
Original code:
def fibonacci(n):
    if n<=1:return n
    return fibonacci(n-1)+fibonacci(n-2)

Formatted with black:
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
```

---

## 📊 Diagram: Formatting Pipeline

```
┌────────────────────────────────────────────────────────────┐
│            LLM Raw Output                                   │
│  "def add(a,b):\n  return a+b"                             │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────┐
│            format_code(code, language="python")             │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ↓
              ┌──────────┴──────────┐
              │  Auto-select:       │
              │  python → black     │
              └──────────┬──────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────┐
│            format_python_code()                             │
│  1. Write to temp file: /tmp/tmpXYZ.py                     │
│  2. Run: black --quiet --line-length 88 /tmp/tmpXYZ.py     │
│  3. Read formatted file                                    │
│  4. Delete temp file                                       │
└────────────────────────┬───────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ↓                         ↓
      ✅ Success                 ❌ Error
            │                         │
            │                         ↓
            │                   Try fallback:
            │                   format_with_autopep8()
            │                         │
            ↓                         ↓
    Return formatted            Return original
    "def add(a, b):\n           + error message
        return a + b"
```

---

## 💡 Key Points cho thuyết trình

### 1. Tại sao cần auto-formatting?

**LLM output không consistent:**
```python
# LLM có thể trả về:
"def add(a,b):return a+b"           # Compact
"def add( a , b ): return a + b"    # Random spacing
"def add(a,    b):\n  return a+b"   # Mixed indent
```

**After formatting:**
```python
def add(a, b):
    return a + b
```
**Consistent, professional!**

---

### 2. Fallback strategy

**Robust formatting pipeline:**
```
1. Try black     → Fail
2. Try autopep8  → Fail
3. Normalize     → Always works (lightweight)
```

**Never fail completely!**

---

### 3. Subprocess safety

**Timeout = 5 seconds:**
- Tránh formatter "treo"
- User không phải chờ lâu

**Return original code on error:**
- Better có unformatted code than no code
- User vẫn có thể chỉnh sửa manual

---

### 4. Language-specific conventions

| Language | Indent | Formatter | Style |
|----------|--------|-----------|-------|
| Python | 4 spaces | black | PEP 8 |
| C++ | 2 spaces | clang-format | LLVM/Google |
| JavaScript | 2 spaces | prettier | Standard |

---

### 5. Performance considerations

**Why timeout needed?**
```python
# Worst case: Formatter hangs
# Without timeout: Request treo mãi
# With timeout=5s: Cancel after 5s, return original code
```

**Impact:**
- Most completions: 10-50ms formatting overhead
- Acceptable trade-off cho clean code

---

## 🔧 Usage trong completions.py

```python
# routers/completions.py
from app.core.formatter import format_code, should_format
from app.core.config import settings

async def complete(request: CompletionRequest):
    # ... get LLM completion ...
    completion = llm_response.text
    
    # Optional formatting
    if settings.AUTO_FORMAT and should_format(completion, request.language):
        formatted, error = format_code(completion, request.language)
        
        if error:
            logger.warning(f"Formatting failed: {error}")
            # Keep original completion
        else:
            completion = formatted
            logger.info("Code formatted successfully")
    
    return {"completion": completion}
```

**Flow:**
1. Check config: `AUTO_FORMAT=true`?
2. Check viability: `should_format()`?
3. Format: `format_code()`
4. Fallback if error: Keep original

---

**File này hoàn tất!** 

✅ **ĐÃ HOÀN THÀNH TẤT CẢ FILES TRONG `server/app/core/`:**
1. ✅ `01_config.py.md`
2. ✅ `02_http.py.md`
3. ✅ `03_logging.py.md`
4. ✅ `04_security.py.md`
5. ✅ `05_postprocess.py.md`
6. ✅ `06_formatter.py.md`

**Tiếp theo chúng ta có thể làm:**
- `server/app/middleware/` (request_id middleware)
- `server/app/routers/` (completions, health endpoints)
- `server/app/services/` (groq API integration)
- `src/` (TypeScript extension)

Bạn muốn tôi tiếp tục với phần nào? 🚀
