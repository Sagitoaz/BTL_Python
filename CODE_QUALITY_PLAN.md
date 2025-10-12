# 🔥 CODE COMPLETION QUALITY IMPROVEMENT PLAN

> **URGENT Priority:** Cải thiện chất lượng gợi ý code để đạt mức chuyên nghiệp  
> **Timeline:** Tuần 1 của MVP (Ngày 1-7)  
> **Impact:** Critical cho success của MVP  

---

## 🚨 CURRENT QUALITY ISSUES

### **📊 Test Results Analysis (từ results.csv)**

| Issue | Current State | Target State | Priority |
|-------|---------------|--------------|----------|
| **Markdown Fences** | 80% có ````python` blocks | 0% markdown | 🔴 Critical |
| **Latency P95** | >8000ms | <500ms | 🔴 Critical |
| **Context Accuracy** | Inconsistent, vd: "it" only | Always relevant | 🔴 Critical |
| **Code Quality** | Mixed quality (10-212 tokens) | Consistent professional | 🟡 High |

### **💔 Bad Examples từ Test Results**

```python
# BAD: Current output
```python

    return a + b
```

# GOOD: Target output  
return a + b
```

```python
# BAD: Current context-unaware
Input: "def fibonacci(n):"
Output: "it"  # ← WTF?

# GOOD: Target context-aware
Input: "def fibonacci(n):" 
Output: """
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)"""
```

---

## 🎯 IMPROVEMENT STRATEGY

### **Phase 1: Immediate Fixes (Ngày 1-2)**

#### **1.1 Fix Postprocessing Pipeline**
**File:** `server/app/core/postprocess.py`

```python
# Current: Basic fence stripping
def strip_fences(text: str) -> str:
    t = text
    for fence in FENCES:
        if fence in t:
            t = t.replace(fence, "")
    return t.strip()

# NEW: Aggressive fence removal + validation
def strip_fences_aggressive(text: str) -> str:
    # Remove all markdown patterns
    text = re.sub(r'```\w*\n?', '', text)
    text = re.sub(r'```', '', text)
    text = re.sub(r'~~~\w*\n?', '', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Validate result doesn't start with fence
    if text.startswith('`') or '```' in text:
        # Fallback: extract only code content
        return extract_code_content(text)
    
    return text

def extract_code_content(text: str) -> str:
    """Extract pure code from markdown-wrapped text"""
    # Pattern to match code blocks
    patterns = [
        r'```(?:python|py)?\n(.*?)```',
        r'`([^`]+)`',
        r'~~~(?:python|py)?\n(.*?)~~~'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
    
    # If no pattern matches, return original
    return text
```

#### **1.2 Enhanced Prompt Engineering**
**File:** `server/app/services/ollama.py`

```python
# Current: Basic prompt
def build_prompt(seq: CompleteRequest) -> str:
    rules = [
        f"Return ONLY the missing {seq.language} code.",
        "Never output backticks or any Markdown.",
        # ...existing rules
    ]

# NEW: Context-aware prompt with examples
def build_prompt_v2(seq: CompleteRequest) -> str:
    # Detect completion type
    completion_type = detect_completion_type(seq.prefix, seq.suffix)
    
    if completion_type == "function_body":
        return build_function_completion_prompt(seq)
    elif completion_type == "class_method":
        return build_method_completion_prompt(seq)
    elif completion_type == "inline_expression":
        return build_expression_completion_prompt(seq)
    else:
        return build_general_completion_prompt(seq)

def build_function_completion_prompt(seq: CompleteRequest) -> str:
    return f"""You are a Python code completion AI. Complete ONLY the missing code at <cursor/>.

RULES:
- Output ONLY raw Python code (no markdown, no explanations)
- Respect the existing indentation pattern
- Don't repeat code from prefix or suffix
- Generate syntactically correct Python

EXAMPLE:
Input:
```
def fibonacci(n):
    <cursor/>
    return fibonacci(n-1) + fibonacci(n-2)
```
Output:
```
if n <= 1:
        return n
```

CONTEXT:
<prefix>
{seq.prefix}
</prefix>
<suffix>
{seq.suffix}
</suffix>
<cursor/>

Complete the missing code:"""

def detect_completion_type(prefix: str, suffix: str) -> str:
    """Detect what type of completion is needed"""
    last_line = prefix.split('\n')[-1] if prefix else ""
    
    if re.search(r'def \w+.*:', last_line):
        return "function_body"
    elif re.search(r'class \w+.*:', last_line):
        return "class_body"
    elif re.search(r'^\s*(def|async def)\s+\w+', last_line):
        return "method_body"
    elif '=' in last_line and not last_line.strip().endswith(':'):
        return "inline_expression"
    else:
        return "general"
```

#### **1.3 Response Validation & Quality Control**
**File:** `server/app/core/quality.py` (NEW)

```python
import ast
import re
from typing import Optional, Tuple

def validate_completion_quality(
    completion: str, 
    prefix: str, 
    suffix: str, 
    language: str = "python"
) -> Tuple[bool, Optional[str], str]:
    """
    Validate completion quality before returning to user
    Returns: (is_valid, cleaned_completion, rejection_reason)
    """
    
    if not completion or not completion.strip():
        return False, None, "Empty completion"
    
    # 1. Check for markdown artifacts
    if has_markdown_artifacts(completion):
        cleaned = aggressive_clean_markdown(completion)
        if not cleaned:
            return False, None, "Could not clean markdown"
        completion = cleaned
    
    # 2. Syntax validation for Python
    if language == "python":
        is_valid_syntax, error = validate_python_syntax(completion, prefix, suffix)
        if not is_valid_syntax:
            return False, None, f"Invalid syntax: {error}"
    
    # 3. Context relevance check
    relevance_score = calculate_context_relevance(completion, prefix, suffix)
    if relevance_score < 0.3:  # Threshold for relevance
        return False, None, f"Low context relevance: {relevance_score:.2f}"
    
    # 4. Length and complexity validation
    if len(completion.strip()) < 2:
        return False, None, "Completion too short"
    
    if len(completion) > 1000:  # Reasonable limit
        return False, None, "Completion too long"
    
    return True, completion, "Valid"

def has_markdown_artifacts(text: str) -> bool:
    """Check if text contains markdown artifacts"""
    artifacts = ['```', '~~~', '`', '**', '*', '#', '##']
    return any(artifact in text for artifact in artifacts)

def validate_python_syntax(completion: str, prefix: str, suffix: str) -> Tuple[bool, str]:
    """Validate if completion creates valid Python syntax"""
    try:
        # Try to parse the completion as standalone code
        ast.parse(completion)
        return True, ""
    except SyntaxError as e:
        # Try with context
        try:
            full_code = prefix + completion + suffix
            ast.parse(full_code)
            return True, ""
        except SyntaxError:
            return False, str(e)

def calculate_context_relevance(completion: str, prefix: str, suffix: str) -> float:
    """Calculate how relevant the completion is to the context"""
    
    # Simple heuristics for now - can be improved with ML later
    score = 0.0
    
    # Check if completion uses variables/functions mentioned in prefix
    prefix_tokens = extract_python_identifiers(prefix)
    completion_tokens = extract_python_identifiers(completion)
    
    if prefix_tokens and completion_tokens:
        overlap = len(set(prefix_tokens) & set(completion_tokens))
        score += min(overlap / len(prefix_tokens), 0.5)
    
    # Check indentation consistency
    if maintains_indentation(completion, prefix):
        score += 0.3
    
    # Check if it doesn't duplicate suffix content
    if not duplicates_suffix(completion, suffix):
        score += 0.2
    
    return min(score, 1.0)

def extract_python_identifiers(code: str) -> list:
    """Extract Python identifiers from code"""
    try:
        tree = ast.parse(code)
        identifiers = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.append(node.id)
        return identifiers
    except:
        # Fallback to regex
        return re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code)
```

### **Phase 2: Performance Optimization (Ngày 3-4)**

#### **2.1 Implement Redis Caching**
**File:** `server/app/core/cache.py` (NEW)

```python
import redis
import json
import hashlib
from typing import Optional
from app.core.config import settings

# Redis connection
redis_client = redis.Redis(
    host=getattr(settings, 'REDIS_HOST', 'localhost'),
    port=getattr(settings, 'REDIS_PORT', 6379),
    db=getattr(settings, 'REDIS_DB', 0),
    decode_responses=True
)

def generate_cache_key(prefix: str, suffix: str, language: str, max_tokens: int, temperature: float) -> str:
    """Generate deterministic cache key"""
    content = f"{prefix}|||{suffix}|||{language}|||{max_tokens}|||{temperature}"
    return f"completion:{hashlib.md5(content.encode()).hexdigest()}"

def get_cached_completion(
    prefix: str, 
    suffix: str, 
    language: str, 
    max_tokens: int, 
    temperature: float
) -> Optional[str]:
    """Get cached completion if available"""
    try:
        key = generate_cache_key(prefix, suffix, language, max_tokens, temperature)
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)["completion"]
        return None
    except Exception as e:
        # Log error but don't fail
        print(f"Cache get error: {e}")
        return None

def cache_completion(
    prefix: str, 
    suffix: str, 
    language: str, 
    max_tokens: int, 
    temperature: float, 
    completion: str,
    ttl_seconds: int = 3600  # 1 hour
) -> None:
    """Cache completion result"""
    try:
        key = generate_cache_key(prefix, suffix, language, max_tokens, temperature)
        value = json.dumps({
            "completion": completion,
            "timestamp": time.time()
        })
        redis_client.setex(key, ttl_seconds, value)
    except Exception as e:
        # Log error but don't fail
        print(f"Cache set error: {e}")
```

#### **2.2 Optimize Ollama Parameters**
**File:** `server/app/core/model_config.py` (NEW)

```python
# Optimized model parameters for different scenarios
MODEL_CONFIGS = {
    "fast": {
        "temperature": 0.1,
        "max_tokens": 64,
        "num_predict": 64,
        "num_ctx": 1024,
        "repeat_penalty": 1.05,
        "stop": ["\n\n", "```", "def ", "class ", "if __name__"],
    },
    "balanced": {
        "temperature": 0.2,
        "max_tokens": 128,
        "num_predict": 128,
        "num_ctx": 2048,
        "repeat_penalty": 1.1,
        "stop": ["\n\n", "```", "\n\n#"],
    },
    "creative": {
        "temperature": 0.3,
        "max_tokens": 256,
        "num_predict": 256,  
        "num_ctx": 4096,
        "repeat_penalty": 1.15,
        "stop": ["\n\n\n", "```"],
    }
}

def get_optimal_config(prefix: str, suffix: str, max_tokens: int) -> dict:
    """Choose optimal config based on context"""
    
    # Short completions = fast mode
    if max_tokens <= 64:
        return MODEL_CONFIGS["fast"]
    
    # Function/class definitions = creative mode
    if any(keyword in prefix.lower() for keyword in ["def ", "class ", "async def"]):
        return MODEL_CONFIGS["creative"]
    
    # Default = balanced
    return MODEL_CONFIGS["balanced"]
```

### **Phase 3: Advanced Quality Improvements (Ngày 5-7)**

#### **3.1 Context-Aware Preprocessing**
**File:** `server/app/core/context.py` (NEW)

```python
def preprocess_context(prefix: str, suffix: str) -> Tuple[str, str, dict]:
    """Intelligent context preprocessing"""
    
    # Extract important context information
    context_info = {
        "function_name": extract_current_function(prefix),
        "class_name": extract_current_class(prefix),
        "imports": extract_imports(prefix),
        "variables": extract_variables(prefix),
        "indentation_level": calculate_indentation_level(prefix),
        "completion_type": detect_completion_type(prefix, suffix),
    }
    
    # Smart context trimming (keep most relevant parts)
    optimized_prefix = smart_trim_prefix(prefix, context_info)
    optimized_suffix = smart_trim_suffix(suffix, context_info)
    
    return optimized_prefix, optimized_suffix, context_info

def smart_trim_prefix(prefix: str, context_info: dict) -> str:
    """Keep most relevant prefix content"""
    lines = prefix.split('\n')
    
    # Always keep last 10 lines
    if len(lines) <= 10:
        return prefix
    
    # Keep function/class definitions + last 10 lines
    important_lines = []
    for i, line in enumerate(lines):
        if any(keyword in line for keyword in ["def ", "class ", "import ", "from "]):
            important_lines.append((i, line))
    
    # Combine important lines + recent context
    result_lines = []
    
    # Add imports at the top
    for i, line in important_lines:
        if "import" in line:
            result_lines.append(line)
    
    # Add function/class definitions
    for i, line in important_lines:
        if any(keyword in line for keyword in ["def ", "class "]) and line not in result_lines:
            result_lines.append(line)
    
    # Add recent context (last 5 lines)
    result_lines.extend(lines[-5:])
    
    return '\n'.join(result_lines)
```

#### **3.2 Quality Scoring & Ranking**
**File:** `server/app/core/ranking.py` (NEW)

```python
def score_completion_quality(completion: str, prefix: str, suffix: str) -> float:
    """Score completion quality (0.0 to 1.0)"""
    
    score = 0.0
    
    # Syntax correctness (40% weight)
    if is_syntactically_correct(completion, prefix, suffix):
        score += 0.4
    
    # Context relevance (30% weight)  
    relevance = calculate_context_relevance(completion, prefix, suffix)
    score += relevance * 0.3
    
    # Code quality (20% weight)
    quality = calculate_code_quality(completion)
    score += quality * 0.2
    
    # Length appropriateness (10% weight)
    length_score = calculate_length_score(completion, prefix)
    score += length_score * 0.1
    
    return min(score, 1.0)

def calculate_code_quality(code: str) -> float:
    """Calculate code quality metrics"""
    
    score = 0.0
    
    # Proper naming conventions
    if follows_python_naming(code):
        score += 0.3
    
    # Proper indentation
    if has_consistent_indentation(code):
        score += 0.3
        
    # No obvious bad practices
    if not has_bad_practices(code):
        score += 0.2
        
    # Reasonable complexity
    if has_reasonable_complexity(code):
        score += 0.2
    
    return score

def follows_python_naming(code: str) -> bool:
    """Check if code follows Python naming conventions"""
    # Check for snake_case variables, PascalCase classes, etc.
    # Simplified implementation
    return not re.search(r'\b[A-Z][a-z]+[A-Z]', code)  # No camelCase

def has_bad_practices(code: str) -> bool:
    """Check for obvious bad practices"""
    bad_patterns = [
        r'eval\(',           # eval usage
        r'exec\(',           # exec usage  
        r'import \*',        # wildcard imports
        r'print\(["\']',     # print statements (should use logging)
    ]
    return any(re.search(pattern, code) for pattern in bad_patterns)
```

---

## 📊 SUCCESS METRICS & VALIDATION

### **Quality KPIs (Measured daily)**

| Metric | Current | Week 1 Target | Week 2 Target |
|--------|---------|---------------|---------------|
| **Markdown-free Rate** | 20% | 95% | 99% |
| **P95 Latency** | >8000ms | <1000ms | <500ms |
| **Context Relevance Score** | Low | >0.7 | >0.8 |
| **Syntax Correctness** | ~60% | >90% | >95% |
| **User Satisfaction** | N/A | >7/10 | >8/10 |

### **Automated Quality Tests**

```python
# tools/quality_validation.py
def run_quality_tests():
    """Run comprehensive quality validation"""
    
    test_cases = [
        {
            "name": "function_completion",
            "prefix": "def fibonacci(n):\n    ",
            "suffix": "\n",
            "expected_patterns": [r"if.*n.*<=", r"return.*fibonacci"],
            "forbidden_patterns": [r"```", r"python", r"def fibonacci"]
        },
        {
            "name": "class_method",
            "prefix": "class Calculator:\n    def add(self, a, b):\n        ",
            "suffix": "\n",
            "expected_patterns": [r"return.*a.*\+.*b"],
            "forbidden_patterns": [r"```", r"class Calculator"]
        }
        # ... more test cases
    ]
    
    results = []
    for case in test_cases:
        completion = get_completion(case["prefix"], case["suffix"])
        
        # Check forbidden patterns
        has_forbidden = any(
            re.search(pattern, completion, re.IGNORECASE) 
            for pattern in case["forbidden_patterns"]
        )
        
        # Check expected patterns  
        has_expected = any(
            re.search(pattern, completion, re.IGNORECASE)
            for pattern in case["expected_patterns"]
        )
        
        score = 1.0 if (has_expected and not has_forbidden) else 0.0
        results.append({
            "name": case["name"],
            "score": score,
            "completion": completion
        })
    
    return results
```

---

## 🚀 IMPLEMENTATION TIMELINE

### **Day 1-2: Emergency Fixes**
- [ ] **Morning:** Fix postprocessing pipeline 
- [ ] **Afternoon:** Deploy improved prompt templates
- [ ] **Evening:** Validate fixes with test suite

### **Day 3-4: Performance & Caching**  
- [ ] **Day 3:** Implement Redis caching
- [ ] **Day 4:** Optimize model parameters & test performance

### **Day 5-7: Advanced Quality**
- [ ] **Day 5:** Context preprocessing improvements
- [ ] **Day 6:** Quality scoring system
- [ ] **Day 7:** Integration testing & validation

### **Success Criteria**
By end of Week 1:
- ✅ 0% completions with markdown fences
- ✅ P95 latency < 1000ms  
- ✅ 90% syntax-correct completions
- ✅ User demo shows professional-quality suggestions

---

**🎯 Expected Outcome:** Chuyển từ prototype không sử dụng được thành professional-grade code completion tool sẵn sàng cho production usage!