# Giải thích chi tiết: `server/app/core/postprocess.py`

## 📋 Mục đích của file

File này **làm sạch output từ LLM** để đảm bảo code completion đẹp và đúng format. LLM thường trả về:
- ❌ Markdown fences (```python)
- ❌ Code bị duplicate với prefix/suffix
- ❌ Indentation sai
- ❌ Quá nhiều dòng (không dừng đúng chỗ)

File này fix tất cả vấn đề trên!

---

## 🔍 Phân tích từng function

### 1. Constants & Imports

```python
import re

FENCES = ("```python", "```py", "```", "~~~")
```

**Giải thích:**

**`import re`**
- Regular expression module để pattern matching

**`FENCES`**
- Tuple chứa các markdown fence patterns
- LLM hay bọc code trong markdown blocks
- Ví dụ LLM output:
  ````
  ```python
  def add(a, b):
      return a + b
  ```
  ````
- Ta cần extract chỉ code thuần, không có ```

---

## 🧹 Function 1: `strip_fences(text: str) -> str`

### Mục đích
Xóa **TẤT CẢ** markdown fences khỏi text

### Code phân tích

```python
def strip_fences(text: str) -> str:
    """
    Aggressively remove all markdown fences and code block markers.
    Tries multiple strategies to extract clean code.
    """
```

**"Aggressively"**: Thử nhiều chiến lược để đảm bảo xóa sạch

---

### Strategy 1: Extract từ markdown blocks

```python
    # Strategy 1: Try to extract content from markdown code blocks
    extracted = extract_code_content(text)
    if extracted and extracted != text:
        return extracted.strip()
```

**Giải thích:**
1. Gọi `extract_code_content()` (function chi tiết bên dưới)
2. Nếu extract được code (khác text gốc) → Return ngay
3. `.strip()`: Xóa whitespace đầu/cuối

**Ví dụ:**
```python
text = """```python
def add(a, b):
    return a + b
```"""

extracted = extract_code_content(text)
# → "def add(a, b):\n    return a + b"

# extracted != text → Return extracted ✅
```

---

### Strategy 2: Regex replacement

```python
    # Strategy 2: Remove all fence patterns
    t = text
    # Remove backtick fences with optional language identifier
    t = re.sub(r'```\w*\n?', '', t)
    t = re.sub(r'```', '', t)
```

**Phân tích regex:**

#### `r'```\w*\n?'`

**Breakdown:**
- ` ``` ` → 3 backticks literal
- `\w*` → 0 hoặc nhiều word characters (letters, digits, _)
  - Match: `python`, `py`, `cpp`, `javascript`, etc.
- `\n?` → Optional newline

**Matches:**
```
```python\n  ✅
```py\n     ✅
```\n       ✅
```         ✅ (no newline)
```java123  ✅
```

**Example:**
```python
text = "```python\ndef add():\n    pass\n```"
t = re.sub(r'```\w*\n?', '', text)
# → "def add():\n    pass\n```"
#   (removed ```python\n)

t = re.sub(r'```', '', t)
# → "def add():\n    pass\n"
#   (removed closing ```)
```

---

#### Remove tildes

```python
    # Remove tilde fences
    t = re.sub(r'~~~\w*\n?', '', t)
    t = re.sub(r'~~~', '', t)
```

**Giải thích:**
- Same logic as backticks
- `~~~` also used for markdown code blocks (less common)

---

#### Remove single backticks

```python
    # Remove any remaining single backticks
    t = t.replace('`', '')
```

**Tại sao?**
- Inline code: `variable_name`
- LLM đôi khi dùng single backticks không đúng chỗ

**Example:**
```python
text = "return `a + b`"
t = text.replace('`', '')
# → "return a + b"
```

---

### Strategy 3: Line-by-line cleanup

```python
    result = t.strip()
    
    # Validation: If result still has fences, try line-by-line cleaning
    if '```' in result or '~~~' in result:
        lines = result.split('\n')
        cleaned_lines = [ln for ln in lines if not ln.strip().startswith(('```', '~~~'))]
        result = '\n'.join(cleaned_lines).strip()
```

**Giải thích:**

**Khi nào cần?**
- Strategy 1 & 2 fail (vẫn còn fences)
- Fences nằm giữa code (rare case)

**Logic:**
```python
lines = result.split('\n')  # Split thành từng dòng
cleaned_lines = [
    ln for ln in lines
    if not ln.strip().startswith(('```', '~~~'))
]
# Filter out lines bắt đầu bằng fences
```

**Example:**
```python
result = "def foo():\n```\n    pass\n```"
lines = ["def foo():", "```", "    pass", "```"]
cleaned_lines = ["def foo():", "    pass"]
# → "def foo():\n    pass"
```

---

### Return

```python
    return result
```

---

## 📦 Function 2: `extract_code_content(text: str) -> str`

### Mục đích
Extract code từ markdown blocks, thử nhiều patterns

### Pattern 1: ```python\ncode\n```

```python
    # Pattern 1: ```python\ncode\n```
    match = re.search(r'```(?:python|py)\s*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
```

**Phân tích regex:**

#### `r'```(?:python|py)\s*\n(.*?)```'`

**Breakdown:**
- ` ``` ` → 3 backticks
- `(?:python|py)` → Non-capturing group, match "python" OR "py"
- `\s*` → 0+ whitespace
- `\n` → Newline
- `(.*?)` → **Capturing group**: Match anything (non-greedy)
- ` ``` ` → Closing backticks

**`re.DOTALL`:**
- `.` matches newlines too
- Cho phép capture multi-line code

**Example:**
```python
text = """```python
def add(a, b):
    return a + b
```"""

match = re.search(r'```(?:python|py)\s*\n(.*?)```', text, re.DOTALL)
# match.group(0) = whole match = "```python\ndef add(a, b):\n    return a + b\n```"
# match.group(1) = captured group = "def add(a, b):\n    return a + b"

return match.group(1).strip()
# → "def add(a, b):\n    return a + b"
```

---

### Pattern 2: Generic ```\ncode\n```

```python
    # Pattern 2: ```\ncode\n```
    match = re.search(r'```\s*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
```

**Giải thích:**
- Same as Pattern 1 nhưng không yêu cầu language
- Fallback nếu LLM không specify language

**Example:**
```python
text = """```
return a + b
```"""

# Pattern 1 fail (no "python" keyword)
# Pattern 2 match ✅
match = re.search(r'```\s*\n(.*?)```', text, re.DOTALL)
# → "return a + b"
```

---

### Pattern 3: Tilde fences

```python
    # Pattern 3: ~~~python\ncode\n~~~
    match = re.search(r'~~~(?:python|py)?\s*\n(.*?)~~~', text, re.DOTALL)
    if match:
        return match.group(1).strip()
```

**Giải thích:**
- Markdown cũng support `~~~` thay vì ` ``` `
- `(?:python|py)?` → Optional language

---

### Pattern 4: Inline backticks

```python
    # Pattern 4: Single backticks for inline code
    match = re.search(r'`([^`]+)`', text)
    if match and '\n' not in match.group(1):
        return match.group(1).strip()
```

**Phân tích:**

#### `r'`([^`]+)`'`

**Breakdown:**
- `` ` `` → Opening backtick
- `([^`]+)` → Capturing group: 1+ chars NOT backtick
- `` ` `` → Closing backtick

**`'\n' not in match.group(1)`:**
- Chỉ match inline code (single line)
- Multi-line code đã được handle ở patterns trên

**Example:**
```python
text = "The function is `add(a, b)`"
match = re.search(r'`([^`]+)`', text)
# → "add(a, b)"

text = "Code: `def foo():\n    pass`"
match = re.search(r'`([^`]+)`', text)
# match.group(1) = "def foo():\n    pass"
# '\n' in match → Skip (multi-line)
```

---

### Fallback

```python
    # No markdown found, return original
    return text
```

**Khi nào?**
- Text không có markdown
- LLM trả về code thuần

---

## ✂️ Function 3: `cut_at_stops(text: str, stops: list[str]) -> str`

### Mục đích
Cắt completion tại stop sequences (tránh generate quá nhiều)

### Code

```python
def cut_at_stops(text: str, stops: list[str]) -> str:
    """Cut text at first occurrence of any stop sequence."""
    if not stops:
        return text
    
    idxs = [text.find(s) for s in stops if text.find(s) >= 0]
    if not idxs:
        return text
    
    cut_point = min(idxs)
    return text[:cut_point]
```

**Phân tích logic:**

### Step 1: Check empty stops

```python
    if not stops:
        return text
```

**Khi nào?**
- `stops = []` hoặc `stops = None`
- Không cần cut → Return nguyên

---

### Step 2: Find all stop positions

```python
    idxs = [text.find(s) for s in stops if text.find(s) >= 0]
```

**Giải thích:**

**`text.find(s)`:**
- Tìm vị trí đầu tiên của substring `s`
- Return index (0-based) nếu tìm thấy
- Return `-1` nếu không tìm thấy

**`if text.find(s) >= 0`:**
- Filter out stops không có trong text

**Example:**
```python
text = "def add(a, b):\n    return a + b\n\ndef subtract(a, b):"
stops = ["\n\n", "def ", "class "]

# text.find("\n\n") = 30 ✅
# text.find("def ") = 0 ✅
# text.find("class ") = -1 ❌

idxs = [30, 0]  # Chỉ giữ >= 0
```

---

### Step 3: Find earliest stop

```python
    if not idxs:
        return text
    
    cut_point = min(idxs)
```

**Giải thích:**
- `min(idxs)`: Vị trí gần nhất (cắt sớm nhất)
- Nếu không có stop nào → Return nguyên

**Example:**
```python
idxs = [30, 0]
cut_point = min(idxs) = 0
```

---

### Step 4: Cut text

```python
    return text[:cut_point]
```

**Example:**
```python
text = "def add(a, b):\n    return a + b\n\ndef subtract(a, b):"
cut_point = 30  # Vị trí "\n\n"

result = text[:30]
# → "def add(a, b):\n    return a + b"
# (Stopped before "\n\n", không generate thêm function)
```

---

### Use case

**Problem:** LLM generate quá nhiều code

```python
# User chỉ cần complete 1 function:
def fibonacci(n):
    █

# LLM trả về (quá nhiều):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):  # ← Không cần!
    if n <= 1:
        return 1
    return n * factorial(n-1)

class Math:  # ← Không cần!
    ...
```

**Solution:** Stop sequences

```python
stops = ["\n\n", "def ", "class "]
result = cut_at_stops(llm_output, stops)
# → Cắt tại "\n\n" (trước "def factorial")
# User chỉ nhận 1 function ✅
```

---

## 📏 Function 4: `last_line_indent(prefix: str) -> int`

### Mục đích
Tính indentation của dòng cuối cùng trong prefix

### Code

```python
def last_line_indent(prefix: str) -> int:
    if not prefix:
        return 0
    last = prefix.splitlines()[-1]
    return len(last) - len(last.lstrip(" "))
```

**Phân tích:**

### `prefix.splitlines()[-1]`

**Giải thích:**
- `.splitlines()`: Split theo newlines, return list dòng
- `[-1]`: Lấy dòng cuối cùng

**Example:**
```python
prefix = "def foo():\n    if x > 0:\n        "
lines = prefix.splitlines()
# → ["def foo():", "    if x > 0:", "        "]

last = lines[-1]
# → "        " (8 spaces)
```

---

### `len(last) - len(last.lstrip(" "))`

**Giải thích:**
- `len(last)`: Độ dài cả dòng (including spaces)
- `last.lstrip(" ")`: Remove leading spaces
- `len(last.lstrip(" "))`: Độ dài phần còn lại
- Difference = số spaces đầu dòng

**Example:**
```python
last = "        return x"  # 8 spaces + "return x"
len(last) = 16
len(last.lstrip(" ")) = 8  # "return x"
indent = 16 - 8 = 8 ✅
```

**Edge cases:**
```python
last = "def foo():"  # No leading spaces
len(last) = 9
len(last.lstrip(" ")) = 9
indent = 0 ✅

last = "    "  # Only spaces
len(last) = 4
len(last.lstrip(" ")) = 0  # Empty string
indent = 4 ✅
```

---

## 🎯 Function 5: `align_first_line(prefix: str, completion: str) -> str`

### Mục đích
**QUAN TRỌNG NHẤT:** Align indentation của completion với prefix

### Tại sao cần?

**Problem:**
```python
# Prefix (cursor ở đây):
def foo():
    if x > 0:
        █

# LLM trả về (indent = 0):
return x

# Result (SAI):
def foo():
    if x > 0:
return x  # ← Indent sai! Nên là 8 spaces
```

**Solution:** `align_first_line()` sửa indent

---

### Code phân tích (phần 1)

```python
def align_first_line(prefix: str, completion: str) -> str:
    """
    Align the first line of completion with the indentation of the last line in prefix.
    Preserve relative indentation for multi-line completions.
    
    LIMITATIONS: Python dedent keywords (elif, else, except, finally) are not automatically
    handled. Users should manually position cursor at the correct indentation level.
    """
```

**Limitations note:**
- `elif`, `else`, `except`, `finally` cần dedent (giảm indent)
- User phải đặt cursor đúng vị trí
- Không tự động detect các keywords này

---

### Check empty completion

```python
    if not completion:
        return completion
    
    lines = completion.splitlines()
    if not lines:
        return completion
```

---

### Detect prefix ends with indent

```python
    # Check if prefix ends with whitespace (indent already provided)
    prefix_ends_with_indent = prefix and prefix[-1] in (' ', '\t')
```

**Giải thích:**

**Tại sao check?**
- **Case 1:** Prefix ends with code → Cần thêm indent
  ```python
  prefix = "def foo():\n    if x > 0:"  # Ends with ":"
  # → completion cần indent mới
  ```

- **Case 2:** Prefix ends with spaces → Indent đã có
  ```python
  prefix = "def foo():\n    if x > 0:\n        "  # Ends with spaces
  # → completion KHÔNG cần thêm indent
  ```

**Example:**
```python
prefix1 = "def foo():\n    "
prefix1[-1] = ' ' → prefix_ends_with_indent = True

prefix2 = "def foo():"
prefix2[-1] = ':' → prefix_ends_with_indent = False
```

---

### Calculate base indent

```python
    # Calculate base indentation from last line of prefix
    base = last_line_indent(prefix)
```

**Example:**
```python
prefix = "def foo():\n    if x > 0:\n        "
base = last_line_indent(prefix)
# → 8 (8 spaces in last line)
```

---

### Find minimum indent in completion

```python
    # Find the minimum indentation in completion (excluding empty lines)
    min_indent = float('inf')
    for ln in lines:
        if ln.strip():  # Non-empty line
            indent = len(ln) - len(ln.lstrip())
            min_indent = min(min_indent, indent)
    
    if min_indent == float('inf'):
        min_indent = 0
```

**Tại sao cần min_indent?**

**Để tính relative indentation!**

**Example:**
```python
completion = """    if a > 0:
        return a
    return 0"""

lines = ["    if a > 0:", "        return a", "    return 0"]

# Line 1: indent = 4
# Line 2: indent = 8
# Line 3: indent = 4

min_indent = 4

# Relative indents:
# Line 1: 4 - 4 = 0 (base level)
# Line 2: 8 - 4 = 4 (indented +4)
# Line 3: 4 - 4 = 0 (back to base)
```

---

### Process each line

```python
    fixed: list[str] = []
    first_line_target_indent = 0
    
    for i, ln in enumerate(lines):
        # Empty lines pass through unchanged
        if ln.strip() == "":
            fixed.append("")
            continue
```

**Giải thích:**
- Empty lines giữ nguyên (không modify indent)

---

### Calculate line components

```python
        # Calculate current indent and content
        current_indent = len(ln) - len(ln.lstrip())
        content = ln.lstrip()
        relative_indent = current_indent - min_indent
```

**Example:**
```python
ln = "        return a"  # 8 spaces
current_indent = 8
content = "return a"
min_indent = 4
relative_indent = 8 - 4 = 4  # Indented 4 spaces more than base
```

---

### Process first line

```python
        if i == 0:
            # First line: depends on whether prefix ends with indent
            if prefix_ends_with_indent:
                # Prefix already provides indent, first line needs no extra indent
                fixed.append((" " * relative_indent) + content)
                first_line_target_indent = 0
            else:
                # Prefix doesn't provide indent, add base indent
                fixed.append((" " * (base + relative_indent)) + content)
                first_line_target_indent = base
```

**Case 1: prefix_ends_with_indent = True**

```python
prefix = "def foo():\n    if x > 0:\n        "  # 8 spaces at end
completion = "return x"

# prefix already has 8 spaces
# first line just adds content
fixed[0] = "" + "return x" = "return x"
first_line_target_indent = 0

# Final position: 8 spaces (from prefix) + "return x" ✅
```

**Case 2: prefix_ends_with_indent = False**

```python
prefix = "def foo():\n    if x > 0:"  # Ends with ":"
base = 8  # Last line has 8 spaces (counting "    if")
completion = "return x"

# Need to add base indent
fixed[0] = "        " + "return x" = "        return x"
first_line_target_indent = 8

# Insert after ":", new line starts at column 0, needs 8 spaces ✅
```

---

### Process subsequent lines

```python
        else:
            # Subsequent lines: preserve relative indentation from first line
            # They start at column 0 (after newline), so need absolute indent
            fixed.append((" " * (first_line_target_indent + relative_indent)) + content)
```

**Example multi-line:**

```python
prefix = "def foo():"  # base = 0
completion = """    if a > 0:
        return a
    return 0"""

min_indent = 4

# Line 0 (i=0): "    if a > 0:"
#   relative_indent = 0
#   first_line_target_indent = 0
#   fixed[0] = "" + "if a > 0:" = "if a > 0:"  # ❌ Sai! Cần 4 spaces

# WAIT, có vấn đề trong logic này!
```

**🤔 Phát hiện issue trong code:**
- Case trên có bug tiềm ẩn
- Cần review lại logic...

**Thực tế đúng:**
```python
# prefix = "def foo():"
# completion line 0 original indent = 4
# base = 0 (last line of prefix has 0 indent)
# relative_indent = 4 - 4 = 0

# prefix_ends_with_indent = False (ends with ":")
# fixed[0] = (0 + 0) spaces + "if a > 0:" = "if a > 0:"

# Nhưng ta muốn 4 spaces! 
# → Code assume LLM output đã có indent đúng relative
```

**Kết luận:** Logic phức tạp, best practice là LLM output clean (indent từ 0)

---

### Return

```python
    return "\n".join(fixed)
```

---

## ♻️ Functions 6 & 7: Overlap removal

### `cut_overlap_tail(prefix: str, completion: str) -> str`

**Mục đích:** Remove duplicate giữa END of prefix và START of completion

```python
def cut_overlap_tail(prefix: str, completion: str) -> str:
    """
    Remove overlap between end of prefix and start of completion.
    Checks up to 256 chars from end of prefix.
    """
    if not prefix or not completion:
        return completion
    
    # Look at last 256 chars of prefix
    tail = prefix[-256:]
    
    # Try matching lengths from longest to shortest
    max_check = min(len(tail), len(completion), 128)
    
    for k in range(max_check, 0, -1):
        if tail.endswith(completion[:k]):
            # Found overlap of length k, remove it from completion
            return completion[k:]
    
    return completion
```

**Example:**

```python
prefix = "def add(a, b):\n    return"
completion = "return a + b"

tail = "return"  # Last 6 chars
max_check = min(6, 13, 128) = 6

# Try k=6: tail.endswith("return")? YES! ✅
# Remove first 6 chars from completion
result = completion[6:]
# → " a + b"

# Final code:
# "def add(a, b):\n    return" + " a + b"
# → "def add(a, b):\n    return a + b" ✅
```

---

### `cut_overlap_head(suffix: str, completion: str) -> str`

**Mục đích:** Remove duplicate giữa END of completion và START of suffix

```python
def cut_overlap_head(suffix: str, completion: str) -> str:
    """
    Remove overlap between end of completion and start of suffix.
    Checks up to 256 chars from start of suffix.
    """
    if not suffix or not completion:
        return completion
    
    # Look at first 256 chars of suffix
    head = suffix[:256]
    
    # Try matching lengths from longest to shortest
    max_check = min(len(head), len(completion), 128)
    
    for k in range(max_check, 0, -1):
        if completion.endswith(head[:k]):
            # Found overlap of length k, remove it from completion
            return completion[:-k]
    
    return completion
```

**Example:**

```python
prefix = "def add("
suffix = ", b):\n    pass"
completion = "a, b"

head = ", b):\n    pass"
max_check = min(15, 4, 128) = 4

# Try k=4: completion.endswith(", b)")? NO
# Try k=3: completion.endswith(", b")? YES! ✅

result = completion[:-3]
# → "a"

# Final code:
# "def add(" + "a" + ", b):\n    pass"
# → "def add(a, b):\n    pass" ✅
```

---

## 🎯 Main Function: `postprocess()`

### Orchestrates all steps

```python
def postprocess(prefix: str, suffix: str, raw: str, stops: list[str]) -> str:
    t = strip_fences(raw)
    t = cut_at_stops(t, stops)
    t = cut_overlap_tail(prefix, t)
    t = cut_overlap_head(suffix, t)
    t = align_first_line(prefix, t)
    return t.rstrip()
```

**Pipeline:**

```
Raw LLM output
    ↓
1. strip_fences() → Remove ```python, etc.
    ↓
2. cut_at_stops() → Cut at \n\n, def, class
    ↓
3. cut_overlap_tail() → Remove duplicate with prefix end
    ↓
4. cut_overlap_head() → Remove duplicate with suffix start
    ↓
5. align_first_line() → Fix indentation
    ↓
6. .rstrip() → Remove trailing whitespace
    ↓
Clean completion ✅
```

---

## 📊 Complete Example

```python
# Input
prefix = "def fibonacci(n):\n    "
suffix = "\n\nprint(fibonacci(5))"
raw_llm_output = """```python
if n <= 1:
    return n
return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    if n <= 1:
        return 1
```"""
stops = ["\n\n", "def "]

# Step 1: strip_fences
t = "if n <= 1:\n    return n\nreturn fibonacci(n-1) + fibonacci(n-2)\n\ndef factorial(n):\n    if n <= 1:\n        return 1"

# Step 2: cut_at_stops (tìm "\n\n" tại index 56)
t = "if n <= 1:\n    return n\nreturn fibonacci(n-1) + fibonacci(n-2)"

# Step 3: cut_overlap_tail (no overlap)
t = "if n <= 1:\n    return n\nreturn fibonacci(n-1) + fibonacci(n-2)"

# Step 4: cut_overlap_head (no overlap)
t = "if n <= 1:\n    return n\nreturn fibonacci(n-1) + fibonacci(n-2)"

# Step 5: align_first_line (add 4 spaces to each line)
t = "    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"

# Step 6: rstrip
t = "    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"

# Final result:
"""    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)"""

# Combined với prefix:
"""def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)""" ✅
```

---

## 💡 Key Points cho thuyết trình

1. **LLM output không perfect** - Cần postprocessing
2. **Deduplication critical** - Tránh code bị repeat
3. **Indentation** - Python yêu cầu indent đúng
4. **Stop sequences** - Tránh generate quá nhiều
5. **Multiple strategies** - Thử nhiều cách để robust

---

**File này hoàn tất!** Tiếp theo: `formatter.py`. Tiếp không? 🎯
