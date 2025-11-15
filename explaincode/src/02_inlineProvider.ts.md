# Giải thích chi tiết: `src/inlineProvider.ts`

## 📋 Mục đích của file

File này implement **InlineCompletionItemProvider** - CORE LOGIC:
1. **Provide inline completions** khi user đang gõ code
2. **Smart indentation** (tabs/spaces, auto-indent)
3. **Comment-to-code generation** (từ comment → code)
4. **Import detection** (detect missing imports)
5. **Deduplication** (remove repeated code)
6. **Feedback tracking** (acceptance/rejection)
7. **Streaming support** (SSE for real-time)
8. **User personalization** (SHA-256 hashed user ID)

**Đây là FILE QUAN TRỌNG NHẤT** của extension! 🎯

---

## 🔍 Phân tích từng phần

### Import statements

```typescript
import * as vscode from 'vscode';
import * as crypto from 'crypto';
```

**Giải thích:**
- `vscode`: VS Code Extension API
- `crypto`: SHA-256 hashing for user ID

---

### Constants

```typescript
const DEFAULT_STOPS_PY = ["\n\n", "\n\n```", "\n\n##", "\n\n# ", "\n\n\"\"\"", "\n\n'''"];
const DEFAULT_STOPS_CPP = ["\n\n", "\n\n```", "\n\n//", "\n\n/*", "\n\n#endif"];
const DEFAULT_TEMPERATURE = 0.2; // Lower for more deterministic code
const DEFAULT_MAX_TOKENS = 300; // Longer for multi-line completions
const MAX_SIDE_CHARS = 8000; // More context
```

---

### Phân tích Constants

#### Stop Sequences (Python)

```typescript
const DEFAULT_STOPS_PY = ["\n\n", "\n\n```", "\n\n##", "\n\n# ", "\n\n\"\"\"", "\n\n'''"];
```

**Purpose:** Tell LLM when to stop generating

**Each stop:**

**`"\n\n"`** - Double newline
```python
def add(a, b):
    return a + b

← Stop here (function complete)
```

**`"\n\n```"`** - Markdown fence
```python
def add(a, b):
    return a + b

```← Stop (prevents markdown)
```

**`"\n\n##"`** - Markdown heading
```python
def add(a, b):
    return a + b

## ← Stop (prevents markdown heading)
```

**`"\n\n# "`** - Comment section
```python
def add(a, b):
    return a + b

# ← Stop (new section starts)
```

**`"\n\n\"\"\""`** - Docstring
```python
def add(a, b):
    return a + b

"""← Stop (new docstring)
```

**`"\n\n'''"`** - Alt docstring
```python
def add(a, b):
    return a + b

'''← Stop
```

---

#### Stop Sequences (C++)

```typescript
const DEFAULT_STOPS_CPP = ["\n\n", "\n\n```", "\n\n//", "\n\n/*", "\n\n#endif"];
```

**C++-specific stops:**

**`"\n\n//"`** - Single-line comment
```cpp
int add(int a, int b) {
    return a + b;
}

// ← Stop (new section)
```

**`"\n\n/*"`** - Multi-line comment
```cpp
int add(int a, int b) {
    return a + b;
}

/*← Stop
```

**`"\n\n#endif"`** - Preprocessor directive
```cpp
int add(int a, int b) {
    return a + b;
}

#endif ← Stop (end of header guard)
```

---

#### Temperature

```typescript
const DEFAULT_TEMPERATURE = 0.2;
```

**Low temperature for code:**
- 0.0 = Completely deterministic (always same output)
- 0.2 = Slight variation (good for code) ✅
- 0.5 = Balanced
- 1.0 = Very creative (bad for code)

**Why 0.2?**
- Code needs consistency
- Math/logic should be deterministic
- But allow some variation for variable names

---

#### Max Tokens

```typescript
const DEFAULT_MAX_TOKENS = 300;
```

**300 tokens ≈ 200-250 words**

**Enough for:**
- Multi-line functions (10-20 lines)
- Class methods
- Complex logic

**Not enough for:**
- Entire classes (would need 1000+)
- Multiple functions (by design!)

---

#### Context Window

```typescript
const MAX_SIDE_CHARS = 8000;
```

**8000 chars ≈ 100-150 lines of code**

**Split evenly:**
- Prefix: 8000 chars max
- Suffix: 8000 chars max
- Total context: 16,000 chars

**Why limit?**
- LLM context window limits (4096-8192 tokens)
- API payload size limits
- Performance (less to process)

---

## 🆔 Function: `getUserId()`

### Purpose
**Generate anonymous user ID** from machine ID

### Code

```typescript
function getUserId(): string {
  const machineId = vscode.env.machineId;
  const hash = crypto.createHash('sha256').update(machineId).digest('hex');
  return hash.substring(0, 16); // Use first 16 chars for brevity
}
```

---

### Phân tích Step-by-Step

#### Get Machine ID

```typescript
const machineId = vscode.env.machineId;
```

**VS Code provides unique machine ID:**
- Persistent per installation
- Same across VS Code restarts
- Changes if reinstall VS Code
- Example: `"550e8400-e29b-41d4-a716-446655440000"`

---

#### SHA-256 Hashing

```typescript
const hash = crypto.createHash('sha256').update(machineId).digest('hex');
```

**Process:**
```
machineId = "550e8400-e29b-41d4-a716-446655440000"
    ↓
SHA-256 hash
    ↓
hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
```

**Properties:**
- ✅ One-way (can't reverse)
- ✅ Deterministic (same input → same output)
- ✅ Unique (different inputs → different hashes)
- ✅ Anonymous (can't identify user)

---

#### Truncate to 16 chars

```typescript
return hash.substring(0, 16);
```

**Result:**
```
"e3b0c44298fc1c14"
```

**Why 16 chars?**
- Still very unique (2^64 combinations)
- Shorter for logs
- Easier to read
- Saves bandwidth

---

## 📏 Function: `detectIndentation()`

### Purpose
**Detect editor's indent settings** (tabs vs spaces, size)

### Code

```typescript
function detectIndentation(doc: vscode.TextDocument): { char: string, size: number } {
  const config = vscode.workspace.getConfiguration('editor', doc.uri);
  const insertSpaces = config.get<boolean>('insertSpaces', true);
  const tabSize = config.get<number>('tabSize', 4);
  
  if (insertSpaces) {
    return { char: ' ', size: tabSize };
  }
  return { char: '\t', size: 1 };
}
```

---

### Phân tích

#### Get Editor Config

```typescript
const config = vscode.workspace.getConfiguration('editor', doc.uri);
```

**Reads settings.json:**
```json
{
  "editor.insertSpaces": true,
  "editor.tabSize": 4
}
```

**Per-document URI:**
- Can have different settings per file
- Respects `.editorconfig`
- Language-specific overrides

---

#### Check Insert Spaces

```typescript
const insertSpaces = config.get<boolean>('insertSpaces', true);
```

**Default:** `true` (use spaces)

**Options:**
- `true`: Tab key inserts spaces
- `false`: Tab key inserts tab character

---

#### Get Tab Size

```typescript
const tabSize = config.get<number>('tabSize', 4);
```

**Default:** 4 spaces

**Common values:**
- 2 spaces (JavaScript, Google style)
- 4 spaces (Python PEP 8)
- 8 spaces (Go, Linux kernel)

---

#### Return Indent Info

```typescript
if (insertSpaces) {
  return { char: ' ', size: tabSize };
}
return { char: '\t', size: 1 };
```

**Examples:**

**Spaces (insertSpaces=true, tabSize=4):**
```typescript
{ char: ' ', size: 4 }
// One indent level = "    " (4 spaces)
```

**Tabs (insertSpaces=false):**
```typescript
{ char: '\t', size: 1 }
// One indent level = "\t" (1 tab char)
```

---

## 📐 Function: `getIndentFromLine()`

### Purpose
**Extract indent string** from line start

### Code

```typescript
function getIndentFromLine(line: string): string {
  const match = line.match(/^(\s*)/);
  return match ? match[1] : '';
}
```

---

### Phân tích

#### Regex: `^(\s*)`

**Breakdown:**
- `^` - Start of string
- `(\s*)` - Capture group: zero or more whitespace
- Matches all leading whitespace

**Examples:**

```typescript
getIndentFromLine("    return True")
// → "    " (4 spaces)

getIndentFromLine("\t\treturn True")
// → "\t\t" (2 tabs)

getIndentFromLine("return True")
// → "" (no indent)

getIndentFromLine("  \t  x = 10")
// → "  \t  " (mixed spaces and tabs)
```

---

## 🔢 Function: `getIndentLevel()`

### Purpose
**Calculate indent level** (number of indent units)

### Code

```typescript
function getIndentLevel(indent: string, indentChar: string, indentSize: number): number {
  if (indentChar === '\t') {
    return indent.split('\t').length - 1;
  }
  return Math.floor(indent.length / indentSize);
}
```

---

### Phân tích

#### Tab-based Indentation

```typescript
if (indentChar === '\t') {
  return indent.split('\t').length - 1;
}
```

**Examples:**

```typescript
// One tab:
indent = "\t"
indent.split('\t') = ["", ""]
length = 2
level = 2 - 1 = 1 ✅

// Two tabs:
indent = "\t\t"
indent.split('\t') = ["", "", ""]
length = 3
level = 3 - 1 = 2 ✅

// Three tabs:
indent = "\t\t\t"
indent.split('\t') = ["", "", "", ""]
level = 4 - 1 = 3 ✅
```

---

#### Space-based Indentation

```typescript
return Math.floor(indent.length / indentSize);
```

**Examples:**

```typescript
// 4 spaces, indent size = 4:
indent = "    "
level = Math.floor(4 / 4) = 1 ✅

// 8 spaces, indent size = 4:
indent = "        "
level = Math.floor(8 / 4) = 2 ✅

// 6 spaces, indent size = 4 (partial):
indent = "      "
level = Math.floor(6 / 4) = 1 (not 2!)
```

**Math.floor()** handles incomplete indents:
- 0-3 spaces = level 0
- 4-7 spaces = level 1
- 8-11 spaces = level 2

---

## 🔨 Function: `makeIndent()`

### Purpose
**Create indent string** from level

### Code

```typescript
function makeIndent(level: number, indentChar: string, indentSize: number): string {
  if (indentChar === '\t') {
    return '\t'.repeat(level);
  }
  return ' '.repeat(level * indentSize);
}
```

---

### Phân tích

**Inverse of `getIndentLevel()`**

#### Tabs

```typescript
if (indentChar === '\t') {
  return '\t'.repeat(level);
}
```

**Examples:**
```typescript
makeIndent(0, '\t', 1) // → ""
makeIndent(1, '\t', 1) // → "\t"
makeIndent(2, '\t', 1) // → "\t\t"
makeIndent(3, '\t', 1) // → "\t\t\t"
```

---

#### Spaces

```typescript
return ' '.repeat(level * indentSize);
```

**Examples:**
```typescript
makeIndent(0, ' ', 4) // → ""
makeIndent(1, ' ', 4) // → "    " (4 spaces)
makeIndent(2, ' ', 4) // → "        " (8 spaces)
makeIndent(3, ' ', 4) // → "            " (12 spaces)
```

---

## 💬 Function: `detectCommentIntent()`

### Purpose
**Detect comment-to-code generation** intent

### Code (simplified)

```typescript
function detectCommentIntent(prefix: string, language: string): { isComment: boolean, instruction: string } {
  const lines = prefix.split('\n');
  const lastLine = lines[lines.length - 1] || '';
  const prevLine = lines[lines.length - 2] || '';
  
  // Python comments
  if (language === 'python') {
    // Single line: # TODO: implement this function
    if (lastLine.trim().startsWith('#')) {
      return { isComment: true, instruction: lastLine.trim().substring(1).trim() };
    }
    // Docstring: """Calculate sum of numbers"""
    const docMatch = prefix.match(/"""([^"]+)"""\s*$/s) || prefix.match(/'''([^']+)'''\s*$/s);
    if (docMatch) {
      return { isComment: true, instruction: docMatch[1].trim() };
    }
  }
  
  // C++ comments
  if (language === 'cpp' || language === 'c') {
    // Single line: // TODO: implement addition
    if (lastLine.trim().startsWith('//')) {
      return { isComment: true, instruction: lastLine.trim().substring(2).trim() };
    }
    // Multi-line: /* Calculate factorial */
    const multiMatch = prefix.match(/\/\*([^*]+)\*\/\s*$/s);
    if (multiMatch) {
      return { isComment: true, instruction: multiMatch[1].trim() };
    }
  }
  
  return { isComment: false, instruction: '' };
}
```

---

### Phân tích Comment Detection

#### Python Single-Line Comment

```typescript
if (lastLine.trim().startsWith('#')) {
  return { isComment: true, instruction: lastLine.trim().substring(1).trim() };
}
```

**Example:**
```python
# Calculate factorial of n
← Cursor here
```

**Detection:**
```typescript
lastLine = "# Calculate factorial of n"
lastLine.trim() = "# Calculate factorial of n"
startsWith('#') = true ✅

instruction = lastLine.substring(1).trim()
instruction = " Calculate factorial of n".trim()
instruction = "Calculate factorial of n"

return { isComment: true, instruction: "Calculate factorial of n" }
```

---

#### Python Docstring

```typescript
const docMatch = prefix.match(/"""([^"]+)"""\s*$/s) || prefix.match(/'''([^']+)'''\s*$/s);
if (docMatch) {
  return { isComment: true, instruction: docMatch[1].trim() };
}
```

**Example:**
```python
def calculate():
    """Calculate sum of all numbers"""
    ← Cursor here
```

**Detection:**
```typescript
prefix ends with: """Calculate sum of all numbers"""

docMatch = /"""([^"]+)"""\s*$/s
// Captures: "Calculate sum of all numbers"

instruction = "Calculate sum of all numbers"
return { isComment: true, instruction: "Calculate sum of all numbers" }
```

---

#### C++ Single-Line Comment

```typescript
if (lastLine.trim().startsWith('//')) {
  return { isComment: true, instruction: lastLine.trim().substring(2).trim() };
}
```

**Example:**
```cpp
// Implement binary search
← Cursor here
```

**Detection:**
```typescript
lastLine = "// Implement binary search"
startsWith('//') = true ✅

instruction = lastLine.substring(2).trim()
instruction = " Implement binary search".trim()
instruction = "Implement binary search"
```

---

#### C++ Multi-Line Comment

```typescript
const multiMatch = prefix.match(/\/\*([^*]+)\*\/\s*$/s);
if (multiMatch) {
  return { isComment: true, instruction: multiMatch[1].trim() };
}
```

**Example:**
```cpp
/* Calculate GCD of two numbers */
← Cursor here
```

**Detection:**
```typescript
prefix ends with: /* Calculate GCD of two numbers */

multiMatch = /\/\*([^*]+)\*\/\s*$/s
// Captures: " Calculate GCD of two numbers "

instruction = " Calculate GCD of two numbers ".trim()
instruction = "Calculate GCD of two numbers"
```

---

### Use Case: Comment-to-Code

**Without detection:**
```python
# Calculate factorial
← LLM generates: "# Calculate factorial" (repeats comment!)
```

**With detection:**
```python
# Calculate factorial
← LLM generates actual implementation:
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

**Backend receives:**
```json
{
  "comment_instruction": "Calculate factorial",
  "prefix": "# Calculate factorial\n",
  "suffix": ""
}
```

---

## 📦 Function: `detectMissingImports()`

### Purpose
**Detect missing imports** from generated code

### Code (Python part)

```typescript
function detectMissingImports(completion: string, prefix: string, language: string): string[] {
  const imports: string[] = [];
  
  if (language === 'python') {
    // Find usage patterns like: pd.DataFrame, np.array, os.path
    const matches = completion.matchAll(/\b([a-z_]+)\.([A-Za-z_][A-Za-z0-9_]*)/g);
    const usedModules = new Set<string>();
    for (const match of matches) {
      usedModules.add(match[1]);
    }
    
    // Common module mappings
    const commonImports: Record<string, string> = {
      'pd': 'import pandas as pd',
      'np': 'import numpy as np',
      'plt': 'import matplotlib.pyplot as plt',
      'os': 'import os',
      'sys': 'import sys',
      'json': 'import json',
      're': 'import re',
      'datetime': 'import datetime',
      'math': 'import math',
    };
    
    // Check which imports are missing
    for (const mod of usedModules) {
      const importStatement = commonImports[mod];
      if (importStatement && !prefix.includes(importStatement)) {
        imports.push(importStatement);
      }
    }
    
    // Check for direct function usage
    if (/\bDataFrame\b/.test(completion) && !prefix.includes('pandas')) {
      if (!imports.some(i => i.includes('pandas'))) {
        imports.push('import pandas as pd');
      }
    }
  }
  
  // ... C++ detection ...
  
  return imports;
}
```

---

### Phân tích Import Detection (Python)

#### Pattern Matching

```typescript
const matches = completion.matchAll(/\b([a-z_]+)\.([A-Za-z_][A-Za-z0-9_]*)/g);
```

**Regex:** `\b([a-z_]+)\.([A-Za-z_][A-Za-z0-9_]*)`

**Matches:**
- `pd.DataFrame` → captures `"pd"`
- `np.array` → captures `"np"`
- `os.path.join` → captures `"os"`

**Example:**
```typescript
completion = "df = pd.DataFrame(data)\narr = np.array([1, 2, 3])"

matches:
- match[0] = "pd.DataFrame", match[1] = "pd"
- match[0] = "np.array", match[1] = "np"

usedModules = Set(["pd", "np"])
```

---

#### Common Module Mappings

```typescript
const commonImports: Record<string, string> = {
  'pd': 'import pandas as pd',
  'np': 'import numpy as np',
  'plt': 'import matplotlib.pyplot as plt',
  ...
};
```

**Maps alias → import statement**

**Why needed?**
```python
# User uses:
df = pd.DataFrame(data)

# Need to suggest:
import pandas as pd  ← Not just "import pd"!
```

---

#### Check Missing Imports

```typescript
for (const mod of usedModules) {
  const importStatement = commonImports[mod];
  if (importStatement && !prefix.includes(importStatement)) {
    imports.push(importStatement);
  }
}
```

**Logic:**
1. For each used module (`pd`, `np`, etc.)
2. Get import statement from mapping
3. Check if already in prefix (file start)
4. If not → add to suggestions

**Example:**
```typescript
// Completion uses:
completion = "df = pd.DataFrame(data)"

// Prefix (existing code):
prefix = "import numpy as np\n\n"

// usedModules = ["pd"]
// "import pandas as pd" not in prefix ✅
// → imports = ["import pandas as pd"]
```

---

#### Direct Class Detection

```typescript
if (/\bDataFrame\b/.test(completion) && !prefix.includes('pandas')) {
  if (!imports.some(i => i.includes('pandas'))) {
    imports.push('import pandas as pd');
  }
}
```

**Handles direct usage:**
```python
# Completion:
df = DataFrame(data)  ← No "pd." prefix!

# Still detect pandas needed
```

---

### C++ Import Detection

```typescript
if (language === 'cpp' || language === 'c') {
  // Detect std:: usage
  if (/std::(vector|string|map|set|cout|cin)/.test(completion)) {
    if (!prefix.includes('#include <iostream>') && /std::(cout|cin|endl)/.test(completion)) {
      imports.push('#include <iostream>');
    }
    if (!prefix.includes('#include <vector>') && /std::vector/.test(completion)) {
      imports.push('#include <vector>');
    }
    if (!prefix.includes('#include <string>') && /std::string/.test(completion)) {
      imports.push('#include <string>');
    }
    if (!prefix.includes('#include <map>') && /std::map/.test(completion)) {
      imports.push('#include <map>');
    }
  }
}
```

**Example:**
```cpp
// Completion uses:
std::vector<int> nums;
std::cout << "Hello";

// Detects missing:
imports = ["#include <vector>", "#include <iostream>"]
```

---

## 📄 Function: `getPrefixSuffix()`

### Purpose
**Extract prefix and suffix** around cursor

### Code

```typescript
function getPrefixSuffix(doc: vscode.TextDocument, pos: vscode.Position) {
  const start = new vscode.Position(0, 0);
  const end = new vscode.Position(doc.lineCount - 1, doc.lineAt(doc.lineCount - 1).text.length);
  const before = new vscode.Range(start, pos);
  const after = new vscode.Range(pos, end);
  let prefix = doc.getText(before);
  let suffix = doc.getText(after);
  if (prefix.length > MAX_SIDE_CHARS) prefix = prefix.slice(-MAX_SIDE_CHARS);
  if (suffix.length > MAX_SIDE_CHARS) suffix = suffix.slice(0, MAX_SIDE_CHARS);
  return { prefix, suffix };
}
```

---

### Phân tích

#### Define Ranges

```typescript
const start = new vscode.Position(0, 0);
const end = new vscode.Position(doc.lineCount - 1, doc.lineAt(doc.lineCount - 1).text.length);
```

**start:** Beginning of file (line 0, char 0)
**end:** End of last line

---

#### Extract Prefix (before cursor)

```typescript
const before = new vscode.Range(start, pos);
let prefix = doc.getText(before);
```

**Example:**
```python
# File content:
def add(a, b):
    return← Cursor here a + b

# prefix = "def add(a, b):\n    return"
```

---

#### Extract Suffix (after cursor)

```typescript
const after = new vscode.Range(pos, end);
let suffix = doc.getText(after);
```

**Example:**
```python
# File content:
def add(a, b):
    return← Cursor here a + b

# suffix = " a + b"
```

---

#### Truncate to Limits

```typescript
if (prefix.length > MAX_SIDE_CHARS) prefix = prefix.slice(-MAX_SIDE_CHARS);
if (suffix.length > MAX_SIDE_CHARS) suffix = suffix.slice(0, MAX_SIDE_CHARS);
```

**MAX_SIDE_CHARS = 8000**

**Prefix truncation:**
```typescript
prefix.slice(-MAX_SIDE_CHARS)
```
**Takes last 8000 chars** (most recent code matters more!)

**Suffix truncation:**
```typescript
suffix.slice(0, MAX_SIDE_CHARS)
```
**Takes first 8000 chars** (immediate context matters more!)

---

## 🌐 Function: `fetchCompletion()`

### Purpose
**Non-streaming API call** to backend

### Signature

```typescript
async function fetchCompletion(
  serverUrl: string,
  apiKey: string | undefined,
  body: any,
  signal: AbortSignal,
  userId: string | null = null
): Promise<string | null>
```

---

### Step 1: Build Headers

```typescript
const headers: Record<string, string> = {
  "Content-Type": "application/json",
  "Accept": "application/json",
};
if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;
if (userId) headers["X-User-ID"] = userId;
```

**Headers:**
- `Content-Type`: Sending JSON
- `Accept`: Expecting JSON response
- `Authorization`: Optional API key
- `X-User-ID`: Optional user tracking

---

### Step 2: Make Request

```typescript
const url = serverUrl.replace(/\/+$/, "") + "/complete";
const resp = await fetch(url, {
  method: "POST",
  headers,
  body: JSON.stringify(body),
  signal,
});
```

**URL cleanup:**
```typescript
serverUrl.replace(/\/+$/, "")
```
**Removes trailing slashes:**
- `"http://localhost:8000/"` → `"http://localhost:8000"`
- `"http://localhost:8000"` → `"http://localhost:8000"`

**Final URL:** `http://localhost:8000/complete`

---

### Step 3: Handle Errors

```typescript
if (!resp.ok) {
  let errBody = "";
  try { errBody = (await resp.text()).slice(0, 500); } catch { /* noop */ }

  console.error(`[BTL] POST ${url} -> ${resp.status} ${resp.statusText}. Body: ${errBody}`);

  if (resp.status === 401 || resp.status === 403) {
    return null;
  }
  return null;
}
```

**Error handling strategy:**
- Log error to console
- Don't show popup (would interrupt typing!)
- Return null (no completion)

**Special case for 401/403:**
- Authentication errors
- Silent failure (no popup spam)

---

### Step 4: Parse Response

```typescript
let data: ApiResp | null = null;
try {
  data = (await resp.json()) as ApiResp | null;
} catch (e) {
  console.error(`[BTL] JSON parse error từ ${url}:`, e);
  return null;
}

const raw =
  data?.completion ??
  data?.choices?.[0]?.text ??
  "";

if (typeof raw !== "string" || !raw) return null;

const cleaned = stripMdFence(raw).trimEnd();
return cleaned.length ? cleaned : null;
```

**Response formats supported:**

**Format 1: Direct completion**
```json
{
  "completion": "return a + b"
}
```

**Format 2: OpenAI-style choices**
```json
{
  "choices": [
    { "text": "return a + b" }
  ]
}
```

---

## 🌊 Function: `fetchStreamCompletion()`

### Purpose
**Streaming API call** via Server-Sent Events (SSE)

### Signature

```typescript
async function fetchStreamCompletion(
  serverUrl: string,
  apiKey: string | undefined,
  body: any,
  signal: AbortSignal,
  userId: string | null = null
): Promise<string | null>
```

---

### Step 1: Build Headers

```typescript
const headers: Record<string, string> = {
  "Content-Type": "application/json",
};
if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;
if (userId) headers["X-User-ID"] = userId;
```

**Note:** No `Accept: application/json` (expecting SSE stream!)

---

### Step 2: Make Streaming Request

```typescript
const url = serverUrl.replace(/\/+$/, "") + "/complete-stream";
const resp = await fetch(url, {
  method: "POST",
  headers,
  body: JSON.stringify(body),
  signal,
});

if (!resp.ok) {
  // ... error handling (same as fetchCompletion) ...
  return null;
}
```

**Endpoint:** `/complete-stream` (not `/complete`)

---

### Step 3: Parse SSE Stream

```typescript
const reader = resp.body?.getReader();
if (!reader) {
  console.error("[BTL] No readable stream body");
  return null;
}

const decoder = new TextDecoder("utf-8");
let buffer = "";
let fullText = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split("\n");
  buffer = lines.pop() || "";

  for (const line of lines) {
    if (!line.trim()) continue;
    if (line.startsWith("data: ")) {
      const jsonStr = line.substring(6).trim();
      if (jsonStr === "[DONE]") continue;

      try {
        const obj = JSON.parse(jsonStr);
        const chunk = obj?.completion ?? obj?.choices?.[0]?.text ?? obj?.delta ?? "";
        if (typeof chunk === "string") {
          fullText += chunk;
        }
      } catch (err) {
        console.error("[BTL] Failed to parse SSE chunk:", jsonStr, err);
      }
    }
  }
}
```

---

### Phân tích SSE Parsing

#### Get Reader

```typescript
const reader = resp.body?.getReader();
```

**ReadableStream API:**
- Allows reading response chunk by chunk
- More efficient than waiting for full response
- Can cancel mid-stream

---

#### Decode UTF-8

```typescript
const decoder = new TextDecoder("utf-8");
let buffer = "";
let fullText = "";
```

**Variables:**
- `decoder`: Converts bytes → string
- `buffer`: Incomplete lines
- `fullText`: Accumulated completion

---

#### Read Loop

```typescript
while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true });
```

**Each iteration:**
1. Read chunk (bytes)
2. Decode to string
3. Append to buffer

**`{ stream: true }`:** Handles multi-byte UTF-8 characters split across chunks

---

#### Split Lines

```typescript
const lines = buffer.split("\n");
buffer = lines.pop() || "";
```

**Why?**

**Example buffer:**
```
data: {"completion":"return"}\n
data: {"completion":" a + b"}\n
data: [DONE]
```

**After split:**
```typescript
lines = [
  "data: {\"completion\":\"return\"}",
  "data: {\"completion\":\" a + b\"}",
  "data: [DONE]"
]
buffer = "" (last element popped)
```

**If incomplete:**
```
data: {"completion":"ret
```
**Buffer keeps incomplete line** for next iteration!

---

#### Parse SSE Format

```typescript
if (line.startsWith("data: ")) {
  const jsonStr = line.substring(6).trim();
  if (jsonStr === "[DONE]") continue;
```

**SSE format:**
```
data: {"completion": "return a + b"}
data: [DONE]
```

**Extract JSON:**
```typescript
"data: {...}" → {...}
```

---

#### Parse Chunk

```typescript
const obj = JSON.parse(jsonStr);
const chunk = obj?.completion ?? obj?.choices?.[0]?.text ?? obj?.delta ?? "";
if (typeof chunk === "string") {
  fullText += chunk;
}
```

**Supported formats:**

**Format 1:**
```json
{"completion": "return"}
```

**Format 2:**
```json
{"choices": [{"text": "return"}]}
```

**Format 3:**
```json
{"delta": "return"}
```

---

### Step 4: Return Result

```typescript
const cleaned = stripMdFence(fullText).trimEnd();
return cleaned.length ? cleaned : null;
```

Same cleanup as non-streaming version.

---

## 🧹 Function: `stripMdFence()`

### Purpose
**Remove markdown code fences** from LLM output

### Code

```typescript
function stripMdFence(raw: string): string {
  let s = raw.trim();
  // Remove opening fence: ```python or ```cpp
  s = s.replace(/^```(?:python|cpp|c|javascript|typescript|java)?\s*\n?/i, "");
  // Remove closing fence: ```
  s = s.replace(/\n?```\s*$/i, "");
  return s;
}
```

---

### Phân tích

#### Remove Opening Fence

```typescript
s = s.replace(/^```(?:python|cpp|c|javascript|typescript|java)?\s*\n?/i, "");
```

**Regex breakdown:**
- `^` - Start of string
- `` ``` `` - Three backticks
- `(?:python|cpp|...)?` - Optional language identifier
- `\s*` - Optional whitespace
- `\n?` - Optional newline
- `/i` - Case-insensitive

**Examples:**

```typescript
stripMdFence("```python\nreturn a + b")
// → "return a + b"

stripMdFence("```\nreturn a + b")
// → "return a + b"

stripMdFence("```PYTHON\nreturn a + b")
// → "return a + b" (case-insensitive)
```

---

#### Remove Closing Fence

```typescript
s = s.replace(/\n?```\s*$/i, "");
```

**Examples:**

```typescript
stripMdFence("return a + b\n```")
// → "return a + b"

stripMdFence("return a + b\n```   ")
// → "return a + b"
```

---

## 🔧 Function: `getBaseIndent()`

### Purpose
**Get current line's indentation**

### Code

```typescript
function getBaseIndent(doc: vscode.TextDocument, pos: vscode.Position): string {
  const line = doc.lineAt(pos.line).text;
  const match = line.match(/^(\s*)/);
  return match ? match[1] : '';
}
```

**Same as `getIndentFromLine()` but takes document+position**

---

## 📊 Function: `headOverlapLen()`

### Purpose
**Calculate overlap length** between two strings

### Code

```typescript
function headOverlapLen(a: string, b: string): number {
  let len = 0;
  const maxLen = Math.min(a.length, b.length);
  for (let i = 0; i < maxLen; i++) {
    if (a[i] === b[i]) len++;
    else break;
  }
  return len;
}
```

---

### Phân tích

**Compare character by character:**

```typescript
headOverlapLen("return", "return a + b")
// Compare: r=r ✓, e=e ✓, t=t ✓, u=u ✓, r=r ✓, n=n ✓
// Result: 6

headOverlapLen("ret", "return")
// Compare: r=r ✓, e=e ✓, t=t ✓
// Result: 3

headOverlapLen("return", "result")
// Compare: r=r ✓, e=e ✓, t!=s ✗
// Result: 2
```

---

## 🔍 Function: `needsBlockIndent()`

### Purpose
**Check if line needs block indentation** (Python `:`)

### Code

```typescript
function needsBlockIndent(line: string, language: string): boolean {
  if (language !== 'python') return false;
  const trimmed = line.trim();
  return trimmed.endsWith(':');
}
```

---

### Phân tích

**Python-specific:**

```python
def add(a, b):← Ends with ':'
    ← Next line should be indented!

if x > 10:← Ends with ':'
    ← Indent here

for i in range(10):← Ends with ':'
    ← Indent here
```

**Examples:**

```typescript
needsBlockIndent("def add(a, b):", "python")
// → true ✅

needsBlockIndent("return a + b", "python")
// → false (no ':')

needsBlockIndent("int add(int a, int b) {", "cpp")
// → false (not Python)
```

---

## 🧩 Function: `dedupeConsecutiveLinesSoft()`

### Purpose
**Remove duplicate consecutive lines** (soft match)

### Code

```typescript
function dedupeConsecutiveLinesSoft(completion: string, prevLines: string[]): string {
  const completionLines = completion.split('\n');
  const result: string[] = [];
  
  let skipCount = 0;
  for (let i = 0; i < completionLines.length; i++) {
    if (skipCount > 0) {
      skipCount--;
      continue;
    }
    
    const currLine = completionLines[i].trim();
    if (!currLine) {
      result.push(completionLines[i]);
      continue;
    }
    
    // Check if this line (and following lines) match recent code
    let matchLength = 0;
    for (let j = 0; j < prevLines.length && (i + j) < completionLines.length; j++) {
      const prevTrimmed = prevLines[prevLines.length - 1 - j].trim();
      const compTrimmed = completionLines[i + j].trim();
      if (prevTrimmed === compTrimmed) {
        matchLength++;
      } else {
        break;
      }
    }
    
    if (matchLength >= 2) {
      // Skip these duplicate lines
      skipCount = matchLength - 1;
      continue;
    }
    
    result.push(completionLines[i]);
  }
  
  return result.join('\n');
}
```

---

### Phân tích Deduplication

#### Setup

```typescript
const completionLines = completion.split('\n');
const result: string[] = [];
let skipCount = 0;
```

**Variables:**
- `completionLines`: Completion split by line
- `result`: Deduplicated output
- `skipCount`: Lines to skip (part of duplicate block)

---

#### Loop Through Lines

```typescript
for (let i = 0; i < completionLines.length; i++) {
  if (skipCount > 0) {
    skipCount--;
    continue;
  }
```

**Skip mechanism:**
When duplicate block found, skip next N lines

---

#### Check Empty Lines

```typescript
const currLine = completionLines[i].trim();
if (!currLine) {
  result.push(completionLines[i]);
  continue;
}
```

**Always keep empty lines** (don't deduplicate whitespace)

---

#### Match Against Recent Lines

```typescript
let matchLength = 0;
for (let j = 0; j < prevLines.length && (i + j) < completionLines.length; j++) {
  const prevTrimmed = prevLines[prevLines.length - 1 - j].trim();
  const compTrimmed = completionLines[i + j].trim();
  if (prevTrimmed === compTrimmed) {
    matchLength++;
  } else {
    break;
  }
}
```

**Example:**

```python
# Previous lines (prevLines):
["def add(a, b):", "    return a + b"]

# Completion:
"def add(a, b):\n    return a + b\nresult = add(1, 2)"

# Matching:
prevLines[1] = "    return a + b" == completionLines[1] ✓
prevLines[0] = "def add(a, b):" == completionLines[0] ✓
matchLength = 2 ✅
```

---

#### Skip Duplicates

```typescript
if (matchLength >= 2) {
  // Skip these duplicate lines
  skipCount = matchLength - 1;
  continue;
}
```

**Why `>= 2`?**
- Single line match might be coincidence
- 2+ consecutive lines = clear duplicate

**Why `matchLength - 1`?**
- Current line already skipped by `continue`
- Need to skip (matchLength - 1) more lines

---

## 🎯 Function: `leftOverlapLenOnLine()`

### Purpose
**Calculate backward overlap** (suffix already typed)

### Code

```typescript
function leftOverlapLenOnLine(line: string, completion: string): number {
  const trimmedLine = line.trimEnd();
  const trimmedComp = completion.trim();
  
  let maxOverlap = 0;
  for (let i = 1; i <= Math.min(trimmedLine.length, trimmedComp.length); i++) {
    const lineSuffix = trimmedLine.slice(-i);
    const compPrefix = trimmedComp.slice(0, i);
    if (lineSuffix === compPrefix) {
      maxOverlap = i;
    }
  }
  
  return maxOverlap;
}
```

---

### Phân tích

**Find longest overlap:**

```typescript
line = "return "
completion = "return a + b"

// Try i=1:
lineSuffix = " ", compPrefix = "r" → No match

// Try i=2:
lineSuffix = "n ", compPrefix = "re" → No match

// Try i=3:
lineSuffix = "rn ", compPrefix = "ret" → No match

// Try i=4:
lineSuffix = "urn ", compPrefix = "retu" → No match

// Try i=5:
lineSuffix = "turn ", compPrefix = "retur" → No match

// Try i=6:
lineSuffix = "eturn ", compPrefix = "return" → No match

// Try i=7:
lineSuffix = "return ", compPrefix = "return " → MATCH! ✅
maxOverlap = 7
```

**Use case:**
```python
# User already typed:
return a← Cursor

# LLM suggests:
return a + b

# Overlap = 8 chars ("return a")
# Show only: " + b"
```

---

## 🧠 Function: `tidyCompletion()` - MOST COMPLEX!

### Purpose
**Smart indentation and cleanup** of raw LLM completion

### Signature

```typescript
function tidyCompletion(
  raw: string,
  prefix: string,
  suffix: string,
  language: string,
  indentChar: string,
  indentSize: number
): string
```

---

### Algorithm Overview (6 Steps)

**Step 1:** Basic cleaning
**Step 2:** Remove overlap with suffix
**Step 3:** Deduplicate consecutive lines
**Step 4:** Determine block indent needs
**Step 5:** Smart line-by-line indentation
**Step 6:** Final cleanup

---

### Step 1: Basic Cleaning

```typescript
let completion = raw.trim();
completion = stripMdFence(completion);
completion = completion.replace(/\r\n/g, '\n');
if (!completion) return '';
```

**Operations:**
1. Trim whitespace
2. Remove markdown fences
3. Normalize line endings (CRLF → LF)
4. Return empty if nothing left

---

### Step 2: Remove Overlap with Suffix

```typescript
const suffixFirstLine = suffix.split('\n')[0] || '';
if (suffixFirstLine.trim()) {
  const overlap = headOverlapLen(completion, suffixFirstLine);
  if (overlap > 0) {
    completion = completion.slice(overlap);
    if (!completion.trim()) return '';
  }
}
```

---

#### Phân tích Overlap Removal

**Scenario:**

```python
# Cursor position:
return← Cursor a + b

# prefix = "return"
# suffix = " a + b"

# LLM generates:
" a + b"

# overlap = 0 (no overlap)
# Keep full completion ✅
```

**Scenario 2 (with overlap):**

```python
# Cursor position:
ret← Cursor urn a + b

# prefix = "ret"
# suffix = "urn a + b"

# LLM generates:
"urn a + b"

# overlap = 9 ("urn a + b")
# completion = "" (remove all)
# Return empty ✅
```

---

### Step 3: Deduplicate Consecutive Lines

```typescript
const prefixLines = prefix.split('\n');
const recentLines = prefixLines.slice(-5); // Last 5 lines
completion = dedupeConsecutiveLinesSoft(completion, recentLines);
if (!completion.trim()) return '';
```

**Use last 5 lines** to check for duplicates

**Example:**

```python
# Recent lines:
["def add(a, b):", "    return a + b"]

# LLM repeats:
"def add(a, b):\n    return a + b\nresult = add(1, 2)"

# After dedup:
"result = add(1, 2)"
```

---

### Step 4: Determine Block Indent

```typescript
const lines = completion.split('\n');
const lastPrefixLine = prefixLines[prefixLines.length - 1] || '';
const needsIndent = needsBlockIndent(lastPrefixLine, language);
```

**Check if last prefix line ends with `:`**

```python
# lastPrefixLine = "def add(a, b):"
# needsIndent = true ✅
```

---

### Step 5: Smart Line-by-Line Indentation

**THIS IS THE MOST COMPLEX PART!**

```typescript
const currentLineIndent = getIndentFromLine(lastPrefixLine);
const currentLevel = getIndentLevel(currentLineIndent, indentChar, indentSize);

let targetLevel = currentLevel;
if (needsIndent) {
  targetLevel = currentLevel + 1;
}

const result: string[] = [];
for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  const trimmedLine = line.trim();
  
  if (!trimmedLine) {
    result.push('');
    continue;
  }
  
  // Extract original indent from LLM
  const originalIndent = getIndentFromLine(line);
  const originalLevel = getIndentLevel(originalIndent, indentChar, indentSize);
  
  // Calculate relative indent
  let relativeLevel = originalLevel;
  if (i === 0) {
    // First line: use target level
    relativeLevel = targetLevel;
  } else {
    // Subsequent lines: preserve relative indentation
    const firstLineOriginalLevel = getIndentLevel(getIndentFromLine(lines[0]), indentChar, indentSize);
    const delta = originalLevel - firstLineOriginalLevel;
    relativeLevel = targetLevel + delta;
  }
  
  // Ensure non-negative
  if (relativeLevel < 0) relativeLevel = 0;
  
  // Build new line with correct indent
  const newIndent = makeIndent(relativeLevel, indentChar, indentSize);
  result.push(newIndent + trimmedLine);
}

return result.join('\n');
```

---

### Phân tích Smart Indentation

#### Calculate Current Level

```typescript
const currentLineIndent = getIndentFromLine(lastPrefixLine);
const currentLevel = getIndentLevel(currentLineIndent, indentChar, indentSize);
```

**Example:**

```python
# lastPrefixLine = "    def add(a, b):"
# currentLineIndent = "    " (4 spaces)
# currentLevel = 1 (one indent level)
```

---

#### Determine Target Level

```typescript
let targetLevel = currentLevel;
if (needsIndent) {
  targetLevel = currentLevel + 1;
}
```

**Example:**

```python
# currentLevel = 1
# needsIndent = true (ends with ':')
# targetLevel = 2 ✅
```

---

#### Process First Line

```typescript
if (i === 0) {
  // First line: use target level
  relativeLevel = targetLevel;
}
```

**Example:**

```python
# LLM generates:
"return a + b"

# Apply targetLevel = 2:
"        return a + b" (8 spaces)
```

---

#### Process Subsequent Lines

```typescript
else {
  // Subsequent lines: preserve relative indentation
  const firstLineOriginalLevel = getIndentLevel(getIndentFromLine(lines[0]), indentChar, indentSize);
  const delta = originalLevel - firstLineOriginalLevel;
  relativeLevel = targetLevel + delta;
}
```

**Complex example:**

```python
# LLM generates (with its own indentation):
"result = 0\nfor i in range(n):\n    result += i\nreturn result"

# Lines:
[
  "result = 0",           # originalLevel = 0
  "for i in range(n):",   # originalLevel = 0
  "    result += i",      # originalLevel = 1
  "return result"         # originalLevel = 0
]

# firstLineOriginalLevel = 0
# targetLevel = 2

# Line 0: relativeLevel = targetLevel = 2
# Line 1: delta = 0 - 0 = 0, relativeLevel = 2 + 0 = 2
# Line 2: delta = 1 - 0 = 1, relativeLevel = 2 + 1 = 3 ✅
# Line 3: delta = 0 - 0 = 0, relativeLevel = 2 + 0 = 2

# Result:
"        result = 0\n        for i in range(n):\n            result += i\n        return result"
```

**Key insight:** Preserves **relative indentation** from LLM while adjusting to correct base level!

---

### Step 6: Final Cleanup

```typescript
return result.join('\n');
```

Join lines back together with newlines.

---

### Complete Example: tidyCompletion()

**Input:**

```python
# prefix (last line):
"    def add(a, b):"

# LLM raw output:
"```python\nresult = a + b\nif result < 0:\n    return 0\nreturn result\n```"

# suffix:
"\n\nprint(add(1, 2))"

# indentChar = ' ', indentSize = 4
```

**Processing:**

**Step 1: Basic cleaning**
```
"result = a + b\nif result < 0:\n    return 0\nreturn result"
```

**Step 2: Check suffix overlap**
```
suffixFirstLine = ""
No overlap, keep as is
```

**Step 3: Deduplicate**
```
No recent duplicates, keep as is
```

**Step 4: Block indent needed?**
```
lastPrefixLine = "    def add(a, b):"
needsIndent = true ✅
currentLevel = 1
targetLevel = 2
```

**Step 5: Smart indentation**
```
Line 0: "result = a + b" → "        result = a + b" (level 2)
Line 1: "if result < 0:" → "        if result < 0:" (level 2)
Line 2: "    return 0" → "            return 0" (level 3, delta +1)
Line 3: "return result" → "        return result" (level 2)
```

**Step 6: Final result**
```
"        result = a + b\n        if result < 0:\n            return 0\n        return result"
```

**Final code:**
```python
    def add(a, b):
        result = a + b
        if result < 0:
            return 0
        return result
```

**Perfect indentation! 🎉**

---

## 🏗️ Class: `InlineProvider`

### Purpose
**Implements VS Code InlineCompletionItemProvider** interface

### Declaration

```typescript
export class InlineProvider implements vscode.InlineCompletionItemProvider {
  private serverUrl: string;
  private apiKey: string | undefined;
  private enableStreaming: boolean;
  private timeoutMs: number;
  
  private acceptedCompletions: Map<string, { text: string, time: number }> = new Map();
  
  constructor(
    serverUrl: string,
    apiKey: string | undefined,
    enableStreaming: boolean,
    timeoutMs: number
  ) {
    this.serverUrl = serverUrl;
    this.apiKey = apiKey;
    this.enableStreaming = enableStreaming;
    this.timeoutMs = timeoutMs;
  }
```

---

### Properties

**Configuration:**
- `serverUrl`: Backend API URL
- `apiKey`: Optional bearer token
- `enableStreaming`: Use SSE or not
- `timeoutMs`: Request timeout

**State:**
- `acceptedCompletions`: Track accepted suggestions (for feedback)

---

## 📤 Method: `sendCompletionFeedback()`

### Purpose
**Send feedback** when user accepts/rejects completion

### Code

```typescript
async sendCompletionFeedback(
  completionId: string,
  accepted: boolean,
  acceptedText: string | null,
  timeMs: number
): Promise<void> {
  try {
    const url = this.serverUrl.replace(/\/+$/, "") + "/feedback/completion";
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }
    
    const body = {
      completion_id: completionId,
      accepted,
      accepted_text: acceptedText,
      time_ms: timeMs,
    };
    
    const resp = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    
    if (!resp.ok) {
      console.error(`[BTL] Feedback POST failed: ${resp.status}`);
    }
  } catch (err) {
    console.error("[BTL] Feedback error:", err);
  }
}
```

---

### Phân tích Feedback

**POST to `/feedback/completion`:**

```json
{
  "completion_id": "550e8400-e29b-41d4-a716-446655440000",
  "accepted": true,
  "accepted_text": "return a + b",
  "time_ms": 2500
}
```

**Fields:**
- `completion_id`: Unique ID (from response)
- `accepted`: User pressed Tab?
- `accepted_text`: What was inserted
- `time_ms`: How long displayed

**Silent failures:** Don't interrupt user if backend down

---

## ✅ Method: `handleAcceptance()`

### Purpose
**Track accepted completion** for feedback

### Code

```typescript
handleAcceptance(completionId: string, text: string): void {
  this.acceptedCompletions.set(completionId, {
    text,
    time: Date.now(),
  });
}
```

**Simple tracking in Map:**
```typescript
{
  "uuid-123": {
    text: "return a + b",
    time: 1699747200000
  }
}
```

Later sent via `sendCompletionFeedback()`.

---

## 🎯 Method: `provideInlineCompletionItems()` - MAIN METHOD!

### Purpose
**Generate inline completions** when user types

### Signature

```typescript
async provideInlineCompletionItems(
  document: vscode.TextDocument,
  position: vscode.Position,
  context: vscode.InlineCompletionContext,
  token: vscode.CancellationToken
): Promise<vscode.InlineCompletionItem[] | null>
```

---

### Step 1: Validate Document

```typescript
if (!document || position.line < 0) return null;
```

Basic sanity check.

---

### Step 2: Get Prefix/Suffix

```typescript
const { prefix, suffix } = getPrefixSuffix(document, position);
if (!prefix.trim()) return null; // No context
```

**Need some prefix** (can't complete from nothing!)

---

### Step 3: Extract Language

```typescript
const langId = document.languageId;
let language = langId;
if (langId === 'cpp' || langId === 'c') {
  language = 'cpp';
}
```

**Map C/C++ to same language:**
- `cpp` → `cpp`
- `c` → `cpp` (same completion model)

---

### Step 4: Detect Indentation

```typescript
const { char: indentChar, size: indentSize } = detectIndentation(document);
```

Get editor settings (tabs/spaces, size).

---

### Step 5: Comment-to-Code Detection

```typescript
const commentIntent = detectCommentIntent(prefix, language);
let commentInstruction: string | null = null;
if (commentIntent.isComment) {
  commentInstruction = commentIntent.instruction;
}
```

**Check if last line is comment** requesting code generation.

---

### Step 6: Build Request Body

```typescript
const userId = getUserId();

const requestBody: any = {
  language,
  prefix,
  suffix,
  max_tokens: DEFAULT_MAX_TOKENS,
  temperature: DEFAULT_TEMPERATURE,
  stop: language === 'python' ? DEFAULT_STOPS_PY : DEFAULT_STOPS_CPP,
};

if (commentInstruction) {
  requestBody.comment_instruction = commentInstruction;
}
```

---

### Step 7: Make API Call

```typescript
const abortController = new AbortController();
token.onCancellationRequested(() => abortController.abort());

const startTime = Date.now();
let rawCompletion: string | null = null;

if (this.enableStreaming) {
  rawCompletion = await fetchStreamCompletion(
    this.serverUrl,
    this.apiKey,
    requestBody,
    abortController.signal,
    userId
  );
} else {
  rawCompletion = await fetchCompletion(
    this.serverUrl,
    this.apiKey,
    requestBody,
    abortController.signal,
    userId
  );
}

const elapsedMs = Date.now() - startTime;

if (!rawCompletion) return null;
```

**Features:**
- Cancellation support (if user keeps typing)
- Streaming or non-streaming
- Timing measurement

---

### Step 8: Tidy Completion

```typescript
const tidied = tidyCompletion(
  rawCompletion,
  prefix,
  suffix,
  language,
  indentChar,
  indentSize
);

if (!tidied) return null;
```

**Apply smart indentation!**

---

### Step 9: Deduplicate Against Current Line

```typescript
const currentLine = document.lineAt(position.line).text;
const lineBeforeCursor = currentLine.substring(0, position.character);

const overlapLen = leftOverlapLenOnLine(lineBeforeCursor, tidied);
let finalText = tidied;
if (overlapLen > 0) {
  finalText = tidied.substring(overlapLen);
}

if (!finalText.trim()) return null;
```

**Remove text already typed** on current line.

---

### Step 10: Check Forward Overlap

```typescript
const tidiedFirstLine = tidied.split('\n')[0] || '';
const suffixFirstLine = suffix.split('\n')[0] || '';

if (suffixFirstLine.trim()) {
  const fwdOverlap = headOverlapLen(tidiedFirstLine, suffixFirstLine);
  if (fwdOverlap > 0) {
    // Completion would overlap with existing suffix
    return null;
  }
}
```

**Don't suggest code that's already there!**

---

### Step 11: Detect Missing Imports

```typescript
const missingImports = detectMissingImports(tidied, prefix, language);
if (missingImports.length > 0) {
  // Could show notification or auto-add imports
  console.log("[BTL] Missing imports detected:", missingImports);
}
```

**Future enhancement:** Auto-add imports to top of file.

---

### Step 12: Generate Completion ID

```typescript
const completionId = `${userId}-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
```

**Format:** `<userID>-<timestamp>-<random>`

**Example:** `e3b0c44298fc1c14-1699747200000-a7b3x9q`

---

### Step 13: Create InlineCompletionItem

```typescript
const item = new vscode.InlineCompletionItem(finalText);

item.command = {
  command: 'btl.trackAcceptance',
  title: 'Track Acceptance',
  arguments: [completionId, finalText, startTime],
};

return [item];
```

**Command triggers when user accepts** (presses Tab).

---

### Step 14: Track Acceptance (via Command)

**In extension.ts:**

```typescript
vscode.commands.registerCommand('btl.trackAcceptance', 
  async (completionId: string, text: string, startTime: number) => {
    provider.handleAcceptance(completionId, text);
    
    const elapsedMs = Date.now() - startTime;
    await provider.sendCompletionFeedback(completionId, true, text, elapsedMs);
  }
);
```

**Sends feedback to backend:**
- User accepted
- What text was inserted
- How long it took to accept

---

## 🎬 Complete Flow Diagram

```
User types code
      ↓
Trigger: VS Code calls provideInlineCompletionItems()
      ↓
Extract: prefix, suffix, language
      ↓
Detect: comment intent, indentation
      ↓
API Call: POST /complete or /complete-stream
      ↓
Backend: Groq/Ollama generates completion
      ↓
Receive: raw completion text
      ↓
Tidy: Smart indentation (6-step algorithm)
      ↓
Deduplicate: Remove overlaps
      ↓
Check: Missing imports
      ↓
Display: Inline suggestion (gray text)
      ↓
User presses Tab
      ↓
Accept: Insert text
      ↓
Trigger: btl.trackAcceptance command
      ↓
Feedback: POST /feedback/completion
      ↓
Backend: Update user profile
```

---

## 🧪 Test Cases

### Test 1: Basic Completion

**Setup:**
```python
def add(a, b):
    ← Cursor
```

**Expected:**
```python
def add(a, b):
    return a + b← Suggestion
```

**Verification:**
- Correct indentation (8 spaces)
- Logical completion
- No duplicates

---

### Test 2: Comment-to-Code

**Setup:**
```python
# Calculate factorial of n using recursion
← Cursor
```

**Expected:**
```python
# Calculate factorial of n using recursion
def factorial(n):← Suggestion
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

**Verification:**
- Detected comment intent
- Generated implementation
- Proper indentation

---

### Test 3: Import Detection

**Setup:**
```python
# No imports yet

df = pd.DataFrame(data)← Completion
```

**Expected:**
```
Console: [BTL] Missing imports detected: ["import pandas as pd"]
```

**Verification:**
- Detected `pd.DataFrame` usage
- Identified missing `pandas` import

---

### Test 4: Deduplication

**Setup:**
```python
def add(a, b):
    return a + b

def add(a, b):← LLM repeats
    return a + b
result = add(1, 2)← Completion
```

**Expected:**
```python
def add(a, b):
    return a + b

result = add(1, 2)← Only this shown
```

**Verification:**
- Removed duplicate function
- Kept only new code

---

### Test 5: Overlap Handling

**Setup:**
```python
ret← Cursor urn a + b
```
**LLM suggests:** `return a + b`

**Expected:**
No suggestion (would overlap with existing " a + b")

**Verification:**
- Detected forward overlap
- Returned null

---

### Test 6: Streaming vs Non-Streaming

**Setup (Streaming):**
```typescript
enableStreaming = true
```

**Expected:**
- Uses `/complete-stream` endpoint
- Parses SSE chunks
- Same final result as non-streaming

**Verification:**
- Both modes produce identical completions
- Streaming feels faster (progressive rendering)

---

## 📊 Key Points cho Thuyết trình

### 1. Smart Indentation Algorithm

**Highlight:**
- **6-step tidying process** ensures perfect indentation
- **Preserves relative indentation** from LLM output
- **Adapts to user's editor settings** (tabs vs spaces)
- **Handles Python's colon syntax** automatically

**Diagram:**
```
Raw LLM Output → Strip Markdown → Remove Overlaps
                                        ↓
                                  Deduplicate
                                        ↓
                              Detect Block Indent
                                        ↓
                          Line-by-Line Smart Indent
                                        ↓
                              Perfectly Formatted Code
```

---

### 2. Comment-to-Code Generation

**Innovation:**
- Detects **docstrings and comments**
- Extracts **natural language instructions**
- Generates **full implementations** from comments
- Supports **Python, C++, C**

**Example:**
```python
# Calculate factorial
```
→ Complete function implementation!

---

### 3. Deduplication Strategy

**Multi-level:**
- **Suffix overlap:** Don't duplicate existing code ahead
- **Recent lines:** Don't repeat last 5 lines
- **Current line:** Don't repeat what user already typed
- **Soft matching:** Trim whitespace for comparison

**Prevents:**
- Infinite loops
- Redundant suggestions
- User frustration

---

### 4. Import Detection

**Intelligent:**
- **Pattern matching:** `pd.DataFrame`, `np.array`
- **Common libraries:** pandas, numpy, matplotlib
- **Direct usage:** `DataFrame` without alias
- **Language-specific:** Python imports, C++ includes

**Future enhancement:**
- Auto-add imports to file top
- Organize imports (isort style)

---

### 5. Streaming Support

**Benefits:**
- **Real-time feedback** (progressive rendering)
- **Lower latency** (show first lines quickly)
- **Better UX** (feels more responsive)
- **Cancellable** (abort if user keeps typing)

**SSE format:**
```
data: {"completion": "return"}
data: {"completion": " a + b"}
data: [DONE]
```

---

### 6. Feedback Loop

**Complete cycle:**
1. **Generate** completion
2. **Track** acceptance/rejection
3. **Measure** time to accept
4. **Send** feedback to backend
5. **Update** user profile
6. **Personalize** future completions

**Privacy:**
- SHA-256 hashed user IDs
- Anonymous tracking
- No PII collected

---

### 7. Performance Optimizations

**Context limits:**
- Max 8000 chars prefix/suffix
- Prevents huge payloads
- Balances context vs speed

**Cancellation:**
- Abort ongoing requests
- Don't waste resources
- Respond to rapid typing

**Timeouts:**
- Configurable `timeoutMs`
- Fail fast if backend slow
- Don't block editor

---

### 8. Error Handling

**Graceful degradation:**
- **Silent failures** (no popups while typing!)
- **Console logging** (for debugging)
- **Null returns** (no bad suggestions)
- **Try-catch everywhere** (robust)

**Never crash:**
- JSON parse errors → return null
- Network errors → return null
- Timeout → return null
- Invalid response → return null

---

## 🔧 Edge Cases Handled

### Case 1: Empty Completion

```typescript
if (!rawCompletion || !tidied || !finalText.trim()) return null;
```

**Multiple checks** at each stage.

---

### Case 2: Partial UTF-8 Characters

```typescript
decoder.decode(value, { stream: true })
```

**Handles multi-byte chars** split across chunks.

---

### Case 3: Mixed Tabs/Spaces

```typescript
function getIndentLevel(indent: string, indentChar: string, indentSize: number)
```

**Respects user's setting**, doesn't enforce one style.

---

### Case 4: Negative Indent Levels

```typescript
if (relativeLevel < 0) relativeLevel = 0;
```

**Clamps to zero** (can't have negative indentation!).

---

### Case 5: Markdown in Various Positions

```typescript
stripMdFence() // Handles ```python, ```, ```PYTHON, etc.
```

**Removes markdown** regardless of capitalization.

---

## 📈 Complexity Analysis

### Functions by Complexity

**Simple (O(1) or O(n)):**
- `getUserId()` - Hash once
- `detectIndentation()` - Config lookup
- `stripMdFence()` - Regex replace
- `needsBlockIndent()` - String check

**Medium (O(n)):**
- `getIndentFromLine()` - Regex match
- `headOverlapLen()` - Linear scan
- `leftOverlapLenOnLine()` - Loop up to min length
- `fetchCompletion()` - Network I/O

**Complex (O(n²) or higher):**
- `dedupeConsecutiveLinesSoft()` - Nested loops
- `tidyCompletion()` - Multiple passes over lines
- `fetchStreamCompletion()` - SSE parsing with buffering

**Most Complex:**
- `provideInlineCompletionItems()` - 14 steps, orchestrates everything!

---

## 🎯 Architecture Patterns Used

### 1. Provider Pattern
**InlineCompletionItemProvider interface** from VS Code API

### 2. Strategy Pattern
Streaming vs non-streaming (different fetch strategies)

### 3. Template Method Pattern
`tidyCompletion()` - fixed algorithm, customizable steps

### 4. Observer Pattern
Cancellation token subscription

### 5. Builder Pattern
Constructing complex request bodies incrementally

### 6. Factory Pattern
Creating `InlineCompletionItem` objects

---

## 🚀 Summary

**inlineProvider.ts** là **TRÁI TIM** của extension!

**Key innovations:**
1. ✅ **Smart indentation** - 6-step algorithm
2. ✅ **Comment-to-code** - Natural language → implementation
3. ✅ **Deduplication** - Multi-level duplicate removal
4. ✅ **Import detection** - Auto-suggest missing imports
5. ✅ **Streaming support** - Real-time progressive completions
6. ✅ **Feedback loop** - Continuous learning from user
7. ✅ **Privacy-first** - Hashed user IDs
8. ✅ **Robust error handling** - Never interrupts typing

**Lines of code:** 684
**Functions:** 15+
**Classes:** 1 (InlineProvider)
**Complexity:** HIGH (but well-structured!)

**Perfect cho thuyết trình:** Nhiều diagrams, algorithms, và real-world examples! 🎓✨