# Giải thích chi tiết: `server/app/middleware/telemetry.py`

## 📋 Mục đích của file

File này implement **Telemetry Collection System** để:
1. **Thu thập dữ liệu** về các completion requests
2. **Lưu trữ logs** theo định dạng JSONL (daily files)
3. **Anonymize users** để bảo vệ privacy
4. **Export training data** cho model fine-tuning
5. **Generate statistics** về usage patterns

---

## 🔍 Phân tích từng phần

### Import statements

```python
import hashlib
import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
```

**Giải thích:**

- `hashlib`: SHA256 hashing cho anonymization
- `json`: Parse/serialize JSON data
- `logging`: Log operations
- `os`: File system operations
- `defaultdict`: Dict với default values (cho statistics)
- `datetime`: Daily file naming (`telemetry_20251111.jsonl`)
- `Path`: Modern file path handling
- `typing`: Type hints cho maintainability
- `settings`: Config values

---

## 📊 Class: `TelemetryCollector`

### Overview

**Purpose:** Central telemetry collection service

**Key features:**
- 📝 Daily JSONL files
- 🔒 User anonymization (SHA256)
- 📈 Statistics aggregation
- 💾 Training data export

---

## 🔧 Method: `__init__`

### Code

```python
    def __init__(self, data_dir: str = "data/telemetry"):
        """
        data_dir: thu muc luu tru du lieu telemetry
        """
        self.data_dir = Path(data_dir)
        # tao thu muc neu chua ton tai
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
```

---

### Phân tích chi tiết

#### `def __init__(self, data_dir: str = "data/telemetry"):`

**Parameter:**
- `data_dir`: Đường dẫn thư mục lưu telemetry data
- Default: `"data/telemetry"` (relative path)

**Example paths:**
```
project_root/
├── data/
│   └── telemetry/
│       ├── telemetry_20251110.jsonl
│       ├── telemetry_20251111.jsonl
│       └── telemetry_20251112.jsonl
```

---

#### `self.data_dir = Path(data_dir)`

**`Path()` benefits:**
- Cross-platform path handling (Windows/Linux/Mac)
- Modern API (`.mkdir()`, `.exists()`, `.glob()`)
- String operations made easy

**Example:**
```python
# Old way (os.path):
import os
path = os.path.join("data", "telemetry", "file.jsonl")
if not os.path.exists(os.path.dirname(path)):
    os.makedirs(os.path.dirname(path))

# New way (pathlib):
path = Path("data") / "telemetry" / "file.jsonl"
path.parent.mkdir(parents=True, exist_ok=True)  # ✅ Clean!
```

---

#### `self.data_dir.mkdir(parents=True, exist_ok=True)`

**Parameters:**

**`parents=True`:**
- Tạo parent directories nếu chưa tồn tại
- Giống `mkdir -p` trong Linux

**Example:**
```python
Path("data/telemetry/subfolder").mkdir(parents=True)
# Creates:
# data/           ← parent
# data/telemetry  ← parent
# data/telemetry/subfolder  ← target
```

**`exist_ok=True`:**
- Không raise error nếu directory đã tồn tại
- Without this: `FileExistsError`

**Comparison:**
```python
# exist_ok=False (default):
Path("data").mkdir()  # ✅ OK
Path("data").mkdir()  # ❌ FileExistsError!

# exist_ok=True:
Path("data").mkdir(exist_ok=True)  # ✅ OK
Path("data").mkdir(exist_ok=True)  # ✅ OK (no error)
```

---

#### `self.logger = logging.getLogger(__name__)`

**Standard logging pattern:**
- `__name__` = `"app.middleware.telemetry"`
- Logger hierarchy: `app` → `app.middleware` → `app.middleware.telemetry`

**Usage:**
```python
self.logger.info("Telemetry recorded")
self.logger.error("Failed to write telemetry", exc_info=True)
```

---

## 📅 Method: `_get_current_file()`

### Purpose
Generate filename cho daily telemetry file

### Code

```python
    def _get_current_file(self) -> Path:
        """
        Return Path to today's telemetry file (YYYYMMDD).
        """
        today = datetime.now().strftime("%Y%m%d")
        return self.data_dir / f"telemetry_{today}.jsonl"
```

---

### Phân tích chi tiết

#### `datetime.now().strftime("%Y%m%d")`

**Breakdown:**
- `datetime.now()`: Current timestamp
- `.strftime()`: Format as string

**Format codes:**
- `%Y`: Year 4 digits (2025)
- `%m`: Month 2 digits (01-12)
- `%d`: Day 2 digits (01-31)

**Examples:**
```python
# November 11, 2025
datetime.now().strftime("%Y%m%d")  # "20251111"

# December 5, 2025
datetime.now().strftime("%Y%m%d")  # "20251205"
```

---

#### `return self.data_dir / f"telemetry_{today}.jsonl"`

**Path concatenation với `/` operator:**
```python
data_dir = Path("data/telemetry")
today = "20251111"
file_path = data_dir / f"telemetry_{today}.jsonl"

print(file_path)
# → PosixPath('data/telemetry/telemetry_20251111.jsonl')
```

**Tại sao daily files?**

**Advantages:**
1. **Rotation tự động**: Mỗi ngày 1 file mới
2. **Easy cleanup**: Xóa old files by date
3. **Performance**: Smaller file size → faster read/write
4. **Analysis**: Group by date dễ dàng

**Example timeline:**
```
Nov 10: telemetry_20251110.jsonl (1000 requests)
Nov 11: telemetry_20251111.jsonl (1200 requests) ← Today
Nov 12: telemetry_20251112.jsonl (will be created tomorrow)
```

---

## 🔒 Method: `_anonymize_user()`

### Purpose
Hash user identifier để protect privacy (GDPR compliance)

### Code

```python
    def _anonymize_user(self, code: str) -> str:
        """
        Ham ma hoa (hash) code de bao ve nguoi dung (privacy).
        """
        return hashlib.sha256(code.encode("utf-8")).hexdigest()
```

---

### Phân tích chi tiết

#### `hashlib.sha256()`

**SHA256 algorithm:**
- Secure Hash Algorithm 256-bit
- Cryptographic hash function
- One-way (không thể reverse)
- Deterministic (cùng input → cùng output)

**Properties:**
- Output: 64 hex characters (256 bits)
- Collision-resistant
- Fast to compute

---

#### `code.encode("utf-8")`

**Why encode?**
- `sha256()` requires **bytes**, not string
- UTF-8 encoding: Universal, supports all languages

**Example:**
```python
text = "def add(a, b):\n    return a + b"
bytes_data = text.encode("utf-8")

print(type(text))        # <class 'str'>
print(type(bytes_data))  # <class 'bytes'>
print(bytes_data)        # b'def add(a, b):\n    return a + b'
```

---

#### `.hexdigest()`

**Returns hash as hex string:**
```python
hashlib.sha256(b"hello").digest()     # b'\x2c\xf2...' (bytes)
hashlib.sha256(b"hello").hexdigest()  # "2cf24dba5..." (string) ✅
```

---

### Complete Example

```python
# User's code:
code1 = "def add(a, b):\n    return a + b"
code2 = "def add(a, b):\n    return a + b"  # Same
code3 = "def sub(a, b):\n    return a - b"  # Different

# Hash results:
hash1 = _anonymize_user(code1)
# → "3f786850e387550fdab836ed7e6dc881de23001b"

hash2 = _anonymize_user(code2)
# → "3f786850e387550fdab836ed7e6dc881de23001b"  (same!)

hash3 = _anonymize_user(code3)
# → "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a"  (different!)

# Properties:
assert hash1 == hash2  # Same input → same hash ✅
assert hash1 != hash3  # Different input → different hash ✅

# Cannot reverse:
# hash1 → ??? (impossible to get original code)
```

---

### Privacy Implications

**What we DON'T store:**
- ❌ Original code content
- ❌ User names
- ❌ IP addresses

**What we DO store:**
- ✅ Hashed user ID (can track same user over time)
- ✅ Code length (statistics)
- ✅ Language
- ✅ Timestamp

**GDPR compliance:**
```python
# User can be identified by hash within session:
requests = [
    {"user_hash": "3f786850...", "language": "python"},
    {"user_hash": "3f786850...", "language": "python"},  # Same user
]

# But original data cannot be recovered:
"3f786850..." → ??? (original code unknown)
```

---

## 📝 Method: `record_completion()`

### Purpose
**Core method** - Record một completion event vào telemetry

### Code

```python
    def record_completion(
        self,
        language: str,
        prefix: str,
        suffix: str,
        completion: str,
        model: str,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None,
    ):
        """
        Ghi lai thong tin ve mot completion request.
        language: ngon ngu lap trinh
        prefix: code truoc con tro
        suffix: code sau con tro
        completion: ket qua tra ve
        model: ten model su dung
        latency_ms: thoi gian xu ly (milliseconds)
        success: co thanh cong khong
        error: thong bao loi neu co
        """
```

---

### Parameters Explained

#### `language: str`
```python
# Examples:
"python"
"typescript"
"javascript"
"cpp"
```

#### `prefix: str` & `suffix: str`
```python
# User typing code, cursor at |:
prefix = "def add(a, b):\n    |"
suffix = "\n\nprint('test')"

# FIM (Fill-In-the-Middle) context
```

#### `completion: str`
```python
# Model output:
completion = "return a + b"

# Full code after insertion:
# def add(a, b):
#     return a + b
#
# print('test')
```

#### `model: str`
```python
# Examples:
"groq/deepseek-coder-6.7b-instruct"
"groq/llama3-70b"
"groq/mixtral-8x7b"
```

#### `latency_ms: float`
```python
# Time from request → response
latency_ms = 234.56  # 234.56 milliseconds = 0.23 seconds
```

#### `success: bool`
```python
success = True   # Completion successful
success = False  # Error occurred
```

#### `error: Optional[str]`
```python
error = None                    # No error
error = "Timeout: 30s exceeded"  # Error message
error = "Rate limit: 429"        # API error
```

---

### Method Body: Build Entry

```python
        entry = {
            "timestamp": datetime.now().isoformat(),
            "language": language,
            "prefix_len": len(prefix),
            "suffix_len": len(suffix),
            "completion_len": len(completion),
            "model": model,
            "latency_ms": latency_ms,
            "success": success,
            "user_hash": self._anonymize_user(prefix + suffix + completion),
        }
        if error:
            entry["error"] = error
```

---

### Phân tích từng field

#### `"timestamp": datetime.now().isoformat()`

**ISO 8601 format:**
```python
datetime.now().isoformat()
# → "2025-11-11T14:23:45.123456"
#     YYYY-MM-DD T HH:MM:SS.microseconds
```

**Why ISO format?**
- ✅ Standard format (universal)
- ✅ Sortable (string sort = chronological sort)
- ✅ Parseable (all languages support)

---

#### `"prefix_len": len(prefix)`

**Why length instead of content?**

**Privacy + Statistics:**
```python
# ❌ Store original (privacy risk):
{"prefix": "def add(a, b):\n    "}  # Exposes user code!

# ✅ Store length only:
{"prefix_len": 23}  # Safe, still useful for stats
```

**Use cases:**
- Analyze: "Longer prefix → better completions?"
- Track: Average context length over time
- Optimize: "Most users have prefix < 100 chars"

---

#### `"user_hash": self._anonymize_user(prefix + suffix + completion)`

**Concatenate all code:**
```python
prefix = "def add("
suffix = "):\n    return"
completion = "a, b"

combined = prefix + suffix + completion
# → "def add():\n    returna, b"

user_hash = sha256(combined)
# → "e5f2c3a1b..." (unique identifier)
```

**Purpose:**
- Track same user across requests
- User A with similar code patterns → same hash
- User B with different code → different hash

**Statistics possible:**
```python
# User "e5f2c3a1b..." stats:
requests = [
    {"user_hash": "e5f2c3a1b...", "success": True},
    {"user_hash": "e5f2c3a1b...", "success": True},
    {"user_hash": "e5f2c3a1b...", "success": False},
]
# → User has 66% success rate
```

---

#### `if error: entry["error"] = error`

**Conditional field:**
- Only add `"error"` if error exists
- Keeps successful records smaller

**Example entries:**

**Success:**
```json
{
  "timestamp": "2025-11-11T14:23:45.123",
  "language": "python",
  "success": true,
  "latency_ms": 234.5
}
```

**Failure:**
```json
{
  "timestamp": "2025-11-11T14:24:10.456",
  "language": "python",
  "success": false,
  "latency_ms": 5000.0,
  "error": "Timeout: 30s exceeded"
}
```

---

### Write to File

```python
        try:
            file_path = self._get_current_file()
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write telemetry: {e}")
```

---

### Phân tích chi tiết

#### `file_path = self._get_current_file()`

**Gets today's file:**
```python
# November 11, 2025:
file_path = Path("data/telemetry/telemetry_20251111.jsonl")
```

---

#### `with open(file_path, "a", encoding="utf-8") as f:`

**Mode `"a"` (append):**
- Opens file in append mode
- Creates file if doesn't exist
- Writes at end (doesn't overwrite)

**Comparison:**
```python
# "w" mode (write - overwrites!):
with open("file.txt", "w") as f:
    f.write("line1\n")  # File: "line1\n"
with open("file.txt", "w") as f:
    f.write("line2\n")  # File: "line2\n" (line1 lost!)

# "a" mode (append - preserves!):
with open("file.txt", "a") as f:
    f.write("line1\n")  # File: "line1\n"
with open("file.txt", "a") as f:
    f.write("line2\n")  # File: "line1\nline2\n" ✅
```

**`encoding="utf-8"`:**
- Support Unicode characters (Vietnamese, Chinese, etc.)
- Prevents encoding errors

---

#### `json.dumps(entry, ensure_ascii=False)`

**Serialize dict → JSON string:**
```python
entry = {"language": "python", "success": True}
json_str = json.dumps(entry, ensure_ascii=False)
# → '{"language": "python", "success": true}'
```

**`ensure_ascii=False`:**
- Keep Unicode characters as-is
- Don't escape to `\uXXXX`

**Example:**
```python
data = {"error": "Lỗi timeout"}

# ensure_ascii=True (default):
json.dumps(data)
# → '{"error": "L\\u1ed7i timeout"}' ❌ Ugly!

# ensure_ascii=False:
json.dumps(data, ensure_ascii=False)
# → '{"error": "Lỗi timeout"}' ✅ Readable!
```

---

#### `f.write(json.dumps(entry, ensure_ascii=False) + "\n")`

**JSONL format (JSON Lines):**
- Each line = 1 JSON object
- Easy to stream/parse
- Append-friendly

**Example file content:**
```jsonl
{"timestamp": "2025-11-11T14:23:45", "language": "python", "success": true}
{"timestamp": "2025-11-11T14:24:10", "language": "typescript", "success": true}
{"timestamp": "2025-11-11T14:25:33", "language": "python", "success": false}
```

**Why not JSON array?**
```json
[
  {"timestamp": "...", "success": true},
  {"timestamp": "...", "success": true}
]
```

**Problems with JSON array:**
- ❌ Can't append (need to parse entire file, add item, rewrite)
- ❌ Can't stream (must load entire array)
- ❌ Corrupted if incomplete (missing closing `]`)

**JSONL advantages:**
- ✅ Append-friendly (just add new line)
- ✅ Streamable (process line by line)
- ✅ Resilient (corrupt line doesn't break entire file)

---

#### `except Exception as e:`

**Catch all errors:**
```python
# Possible errors:
# - PermissionError (no write access)
# - OSError (disk full)
# - JSONDecodeError (invalid data)
```

**Don't crash the request:**
```python
# ❌ Without try-except:
record_completion(...)  # Disk full!
# → Entire request fails!

# ✅ With try-except:
record_completion(...)  # Disk full, but...
# → Log error, continue request ✅
```

---

## 📊 Method: `get_stats()`

### Purpose
Aggregate statistics từ tất cả telemetry files

### Code

```python
    def get_stats(self) -> Dict[str, Any]:
        """
        Thong ke du lieu telemetry.
        """
        stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "languages": defaultdict(int),
            "models": defaultdict(int),
            "avg_latency_ms": 0.0,
            "total_completion_len": 0,
        }
```

---

### Phân tích structure

#### `defaultdict(int)`

**Auto-initialize missing keys:**
```python
from collections import defaultdict

# Regular dict:
languages = {}
languages["python"] += 1  # ❌ KeyError: 'python'

# Must initialize first:
if "python" not in languages:
    languages["python"] = 0
languages["python"] += 1  # ✅ OK

# defaultdict:
languages = defaultdict(int)  # int() returns 0
languages["python"] += 1  # ✅ OK (auto-creates with 0)
languages["typescript"] += 1  # ✅ OK
print(languages)
# → defaultdict(<class 'int'>, {'python': 1, 'typescript': 1})
```

---

### Read all JSONL files

```python
        latencies = []
        for file in self.data_dir.glob("telemetry_*.jsonl"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        entry = json.loads(line)
```

---

#### `self.data_dir.glob("telemetry_*.jsonl")`

**Pattern matching:**
```python
# Matches:
# ✅ telemetry_20251110.jsonl
# ✅ telemetry_20251111.jsonl
# ✅ telemetry_20251112.jsonl

# Doesn't match:
# ❌ data.json
# ❌ telemetry.txt
# ❌ other_20251111.jsonl
```

**Returns generator:**
```python
files = list(data_dir.glob("telemetry_*.jsonl"))
# → [PosixPath('.../telemetry_20251110.jsonl'),
#    PosixPath('.../telemetry_20251111.jsonl')]
```

---

#### `for line in f:`

**Stream processing:**
- Đọc file line-by-line
- Memory-efficient (không load toàn bộ file)

**Example:**
```python
# 1 GB file with 1 million lines:
with open("huge.jsonl", "r") as f:
    for line in f:  # Only 1 line in memory at a time!
        process(line)
```

---

#### `if not line.strip(): continue`

**Skip empty lines:**
```python
line = "   \n"
line.strip()  # → "" (empty string)
not ""  # → True
# → Skip this line
```

**Why?**
- Blank lines might exist in file
- `json.loads("")` → JSONDecodeError

---

### Aggregate statistics

```python
                        stats["total_requests"] += 1
                        if entry.get("success"):
                            stats["successful_requests"] += 1
                        else:
                            stats["failed_requests"] += 1

                        stats["languages"][entry.get("language", "unknown")] += 1
                        stats["models"][entry.get("model", "unknown")] += 1

                        if "latency_ms" in entry:
                            latencies.append(entry["latency_ms"])
                        stats["total_completion_len"] += entry.get("completion_len", 0)
```

---

#### `entry.get("success")`

**Safe access:**
```python
# entry = {"success": true}
entry.get("success")  # → True

# entry = {} (missing key)
entry.get("success")  # → None (not KeyError!)
entry.get("success", False)  # → False (custom default)
```

---

#### `stats["languages"][entry.get("language", "unknown")] += 1`

**Count by language:**
```python
# First request (Python):
stats["languages"]["python"] += 1
# → {"python": 1}

# Second request (TypeScript):
stats["languages"]["typescript"] += 1
# → {"python": 1, "typescript": 1}

# Third request (Python again):
stats["languages"]["python"] += 1
# → {"python": 2, "typescript": 1}
```

---

#### `latencies.append(entry["latency_ms"])`

**Collect for averaging:**
```python
latencies = []
# Request 1: 200ms
latencies.append(200)
# Request 2: 300ms
latencies.append(300)
# Request 3: 250ms
latencies.append(250)

# Later: avg = sum(latencies) / len(latencies)
# → (200 + 300 + 250) / 3 = 250ms
```

---

### Calculate average latency

```python
            except Exception as e:
                self.logger.warning(f"Error reading {file}: {e}")

        if latencies:
            stats["avg_latency_ms"] = sum(latencies) / len(latencies)

        return stats
```

---

#### `if latencies:`

**Check not empty:**
```python
latencies = []  # Empty
if latencies:  # False
    # Skip (avoid division by zero)

latencies = [200, 300]  # Not empty
if latencies:  # True
    avg = sum(latencies) / len(latencies)
```

---

### Example Output

```python
get_stats()
# Returns:
{
    "total_requests": 150,
    "successful_requests": 145,
    "failed_requests": 5,
    "languages": {
        "python": 80,
        "typescript": 50,
        "javascript": 20
    },
    "models": {
        "groq/deepseek-coder-6.7b-instruct": 100,
        "groq/llama3-70b": 50
    },
    "avg_latency_ms": 245.67,
    "total_completion_len": 15420
}
```

---

## 💾 Method: `export_training_data()`

### Purpose
Export telemetry data → format for LLM fine-tuning

### Code

```python
    def export_training_data(
        self, output_file: str = "training_data.jsonl", format: str = "jsonl"
    ) -> int:
        """
        Xuat du lieu telemetry thanh dinh dang cho training model.
        output_file: ten file xuat ra
        format: dinh dang xuat ra (jsonl hoac csv)
        """
        count = 0
        output_path = Path(output_file)
```

---

### Parameters

#### `output_file: str = "training_data.jsonl"`
- Default filename
- Can override: `export_training_data("my_data.jsonl")`

#### `format: str = "jsonl"`
- `"jsonl"`: JSON Lines format (default)
- `"csv"`: CSV format

---

### Format: JSONL (default)

```python
        if format == "jsonl":
            with open(output_path, "w", encoding="utf-8") as out:
                for file in self.data_dir.glob("telemetry_*.jsonl"):
                    try:
                        with open(file, "r", encoding="utf-8") as f:
                            for line in f:
                                if not line.strip():
                                    continue
                                entry = json.loads(line)
                                if entry.get("success"):
                                    training_entry = {
                                        "prefix": "..." * entry.get("prefix_len", 0),
                                        "suffix": "..." * entry.get("suffix_len", 0),
                                        "completion": "..."
                                        * entry.get("completion_len", 0),
                                        "language": entry.get("language"),
                                        "model": entry.get("model"),
                                    }
                                    out.write(
                                        json.dumps(training_entry, ensure_ascii=False)
                                        + "\n"
                                    )
                                    count += 1
                    except Exception as e:
                        self.logger.warning(f"Error reading {file}: {e}")
```

---

### Phân tích logic

#### `if entry.get("success"):`

**Only export successful completions:**
```python
# ✅ Success → export
{"success": true, "completion_len": 50}  → Export

# ❌ Failure → skip
{"success": false, "error": "Timeout"}  → Skip
```

**Why?**
- Training data should be high-quality
- Failed completions are noisy

---

#### Anonymized training entry

```python
training_entry = {
    "prefix": "..." * entry.get("prefix_len", 0),
    "suffix": "..." * entry.get("suffix_len", 0),
    "completion": "..." * entry.get("completion_len", 0),
    "language": entry.get("language"),
    "model": entry.get("model"),
}
```

**Explanation:**

**`"..." * length`:**
- Placeholder representing length
- NOT actual code (privacy!)

**Example:**
```python
# Original telemetry entry:
{
    "prefix_len": 20,
    "suffix_len": 10,
    "completion_len": 15
}

# Training entry:
{
    "prefix": ".....................",  # 20 chars
    "suffix": "..........",            # 10 chars
    "completion": "...............",    # 15 chars
    "language": "python",
    "model": "groq/deepseek-coder-6.7b-instruct"
}
```

**Purpose:**
- Metadata for training (language, model, lengths)
- NO actual code content (privacy preserved!)

---

### Format: CSV

```python
        elif format == "csv":
            import csv

            with open(output_path, "w", encoding="utf-8", newline="") as out:
                fieldnames = [
                    "timestamp",
                    "language",
                    "prefix_len",
                    "suffix_len",
                    "completion_len",
                    "model",
                    "latency_ms",
                    "success",
                ]
                writer = csv.DictWriter(out, fieldnames=fieldnames)
                writer.writeheader()

                for file in self.data_dir.glob("telemetry_*.jsonl"):
                    try:
                        with open(file, "r", encoding="utf-8") as f:
                            for line in f:
                                if not line.strip():
                                    continue
                                entry = json.loads(line)
                                if entry.get("success"):
                                    row = {
                                        k: entry.get(k)
                                        for k in fieldnames
                                        if k in entry
                                    }
                                    writer.writerow(row)
                                    count += 1
                    except Exception as e:
                        self.logger.warning(f"Error reading {file}: {e}")
```

---

### CSV Format Explained

#### `csv.DictWriter()`

**Write dicts as CSV rows:**
```python
import csv

fieldnames = ["name", "age", "city"]
writer = csv.DictWriter(file, fieldnames=fieldnames)
writer.writeheader()  # Write: name,age,city
writer.writerow({"name": "Alice", "age": 30, "city": "Hanoi"})
# Write: Alice,30,Hanoi
```

---

#### `writer.writeheader()`

**Output:**
```csv
timestamp,language,prefix_len,suffix_len,completion_len,model,latency_ms,success
```

---

#### Dict comprehension

```python
row = {k: entry.get(k) for k in fieldnames if k in entry}
```

**Example:**
```python
fieldnames = ["timestamp", "language", "model", "success"]
entry = {
    "timestamp": "2025-11-11T14:23:45",
    "language": "python",
    "success": True,
    "extra_field": "ignored"
}

row = {k: entry.get(k) for k in fieldnames if k in entry}
# → {"timestamp": "2025-11-11T14:23:45", 
#    "language": "python",
#    "success": True}
# Note: "extra_field" not in fieldnames → excluded
```

---

### Return count

```python
        return count
```

**Usage:**
```python
count = telemetry.export_training_data("my_data.jsonl")
print(f"Exported {count} records")
# → "Exported 145 records"
```

---

## 🔧 Function: `get_telemetry_collector()`

### Purpose
**Singleton pattern** - Ensure only 1 TelemetryCollector instance

### Code

```python
_telemetry_collector_instance: Optional[TelemetryCollector] = None


def get_telemetry_collector() -> TelemetryCollector:
    """
    Lazy singleton cho TelemetryCollector.
    """
    global _telemetry_collector_instance
    if _telemetry_collector_instance is None:
        _telemetry_collector_instance = TelemetryCollector()
    return _telemetry_collector_instance
```

---

### Phân tích pattern

#### Global variable

```python
_telemetry_collector_instance: Optional[TelemetryCollector] = None
```

**Type hint:**
- `Optional[TelemetryCollector]`: Can be `TelemetryCollector` or `None`
- Initially `None`

---

#### Lazy initialization

```python
def get_telemetry_collector() -> TelemetryCollector:
    global _telemetry_collector_instance
    if _telemetry_collector_instance is None:
        _telemetry_collector_instance = TelemetryCollector()
    return _telemetry_collector_instance
```

**First call:**
```python
collector = get_telemetry_collector()
# → _telemetry_collector_instance is None
# → Create new TelemetryCollector()
# → Store in _telemetry_collector_instance
# → Return it
```

**Subsequent calls:**
```python
collector = get_telemetry_collector()
# → _telemetry_collector_instance already exists
# → Return existing instance (no new creation)
```

---

### Why Singleton?

**Problem without singleton:**
```python
# Different parts of code create different instances:
collector1 = TelemetryCollector()
collector2 = TelemetryCollector()
collector3 = TelemetryCollector()

# Problems:
# - Multiple file handles (wasteful)
# - Race conditions (concurrent writes)
# - Inconsistent state
```

**With singleton:**
```python
# All code uses same instance:
collector1 = get_telemetry_collector()
collector2 = get_telemetry_collector()
collector3 = get_telemetry_collector()

assert collector1 is collector2 is collector3  # ✅ Same object!
```

---

## 📊 Complete Usage Example

```python
from app.middleware.telemetry import get_telemetry_collector
import time

# Get singleton instance
telemetry = get_telemetry_collector()

# Record completion
start = time.time()
try:
    completion = generate_completion(prefix, suffix)
    latency = (time.time() - start) * 1000  # Convert to ms
    
    telemetry.record_completion(
        language="python",
        prefix="def add(a, b):\n    ",
        suffix="\n\nprint('test')",
        completion="return a + b",
        model="groq/deepseek-coder-6.7b-instruct",
        latency_ms=latency,
        success=True
    )
except Exception as e:
    latency = (time.time() - start) * 1000
    telemetry.record_completion(
        language="python",
        prefix="def add(a, b):\n    ",
        suffix="",
        completion="",
        model="groq/deepseek-coder-6.7b-instruct",
        latency_ms=latency,
        success=False,
        error=str(e)
    )

# Get statistics
stats = telemetry.get_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Success rate: {stats['successful_requests'] / stats['total_requests'] * 100:.1f}%")
print(f"Avg latency: {stats['avg_latency_ms']:.2f}ms")

# Export training data
count = telemetry.export_training_data("training.jsonl", format="jsonl")
print(f"Exported {count} training examples")
```

---

## 📁 File Structure Example

```
project_root/
├── data/
│   └── telemetry/
│       ├── telemetry_20251109.jsonl  (1000 requests, 2 days old)
│       ├── telemetry_20251110.jsonl  (1200 requests, yesterday)
│       └── telemetry_20251111.jsonl  (300 requests, today)
│
└── training_data.jsonl  (exported training data)
```

**telemetry_20251111.jsonl:**
```jsonl
{"timestamp":"2025-11-11T08:30:15.123","language":"python","prefix_len":20,"suffix_len":10,"completion_len":15,"model":"groq/deepseek-coder-6.7b-instruct","latency_ms":234.5,"success":true,"user_hash":"e5f2c3a1b..."}
{"timestamp":"2025-11-11T08:31:22.456","language":"typescript","prefix_len":35,"suffix_len":5,"completion_len":25,"model":"groq/llama3-70b","latency_ms":456.7,"success":true,"user_hash":"a3d5f7b2c..."}
{"timestamp":"2025-11-11T08:32:10.789","language":"python","prefix_len":50,"suffix_len":0,"completion_len":0,"model":"groq/deepseek-coder-6.7b-instruct","latency_ms":5000.0,"success":false,"error":"Timeout: 30s exceeded","user_hash":"b4e6g8c3d..."}
```

**training_data.jsonl:**
```jsonl
{"prefix":"....................","suffix":"..........","completion":"...............","language":"python","model":"groq/deepseek-coder-6.7b-instruct"}
{"prefix":"...................................","suffix":".....","completion":".........................","language":"typescript","model":"groq/llama3-70b"}
```

---

## 💡 Key Points cho thuyết trình

### 1. Privacy-First Design

**Không lưu code thực:**
```python
# ❌ What we DON'T store:
{"code": "def add(a, b): return a + b"}

# ✅ What we DO store:
{"code_len": 30, "user_hash": "sha256..."}
```

**GDPR compliance:**
- Hashing không thể reverse
- Có thể delete by user_hash
- Thống kê không expose cá nhân

---

### 2. JSONL vs JSON Array

**JSONL advantages:**
```
Append:    O(1) vs O(n)
Stream:    ✅ Yes vs ❌ No
Resilient: ✅ Yes vs ❌ No
```

---

### 3. Daily File Rotation

**Benefits:**
- Auto cleanup old data
- Smaller file sizes
- Easy date-based analysis
- Performance (don't read all history)

---

### 4. Singleton Pattern

**One collector for entire app:**
```python
# ✅ Single file handle
get_telemetry_collector()  # Same instance

# ❌ Multiple instances = problems
TelemetryCollector()  # New instance
TelemetryCollector()  # Another instance (bad!)
```

---

### 5. Statistics Use Cases

**Product decisions:**
- "Python users = 80% → prioritize Python features"
- "Avg latency = 250ms → need optimization"
- "Success rate = 96% → good, but improve 4%"

**Model evaluation:**
- "DeepSeek: 200ms, 98% success"
- "Llama3: 400ms, 95% success"
- → Choose DeepSeek for production

---

### 6. Training Data Export

**Fine-tuning pipeline:**
```
Telemetry JSONL
    ↓
Export successful completions
    ↓
Anonymized training data
    ↓
Fine-tune model on usage patterns
    ↓
Better completions!
```

---

## 🧪 Test Cases

### Test 1: Record completion

```python
from app.middleware.telemetry import get_telemetry_collector
import json

telemetry = get_telemetry_collector()

telemetry.record_completion(
    language="python",
    prefix="def add(",
    suffix="):",
    completion="a, b",
    model="test-model",
    latency_ms=100.0,
    success=True
)

# Check file created
file = telemetry._get_current_file()
assert file.exists()

# Check content
with open(file, "r") as f:
    lines = f.readlines()
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry["language"] == "python"
    assert entry["success"] == True
```

---

### Test 2: User anonymization

```python
code1 = "def add(a, b):"
code2 = "def add(a, b):"
code3 = "def sub(a, b):"

hash1 = telemetry._anonymize_user(code1)
hash2 = telemetry._anonymize_user(code2)
hash3 = telemetry._anonymize_user(code3)

# Same input → same hash
assert hash1 == hash2

# Different input → different hash
assert hash1 != hash3

# Hash properties
assert len(hash1) == 64  # SHA256 = 64 hex chars
assert all(c in "0123456789abcdef" for c in hash1)
```

---

### Test 3: Statistics

```python
# Record multiple completions
for i in range(10):
    telemetry.record_completion(
        language="python",
        prefix="test",
        suffix="",
        completion="test",
        model="test-model",
        latency_ms=100.0 + i * 10,
        success=True
    )

# Record 1 failure
telemetry.record_completion(
    language="python",
    prefix="test",
    suffix="",
    completion="",
    model="test-model",
    latency_ms=5000.0,
    success=False,
    error="Timeout"
)

# Get stats
stats = telemetry.get_stats()
assert stats["total_requests"] == 11
assert stats["successful_requests"] == 10
assert stats["failed_requests"] == 1
assert stats["languages"]["python"] == 11
assert 100.0 <= stats["avg_latency_ms"] <= 600.0  # Range check
```

---

### Test 4: Export training data

```python
import os

# Export JSONL
output = "test_training.jsonl"
count = telemetry.export_training_data(output, format="jsonl")
assert count > 0
assert os.path.exists(output)

# Check content
with open(output, "r") as f:
    for line in f:
        entry = json.loads(line)
        assert "prefix" in entry
        assert "language" in entry
        assert "model" in entry

# Cleanup
os.remove(output)
```

---

**File này hoàn tất!** Tiếp theo: `routers/` directory (completions.py, health.py). Tiếp tục không? 🚀

