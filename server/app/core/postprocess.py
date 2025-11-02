import re

FENCES = ("```python", "```py", "```", "~~~")


def strip_fences(text: str) -> str:
    """
    Aggressively remove all markdown fences and code block markers.
    Tries multiple strategies to extract clean code.
    """
    # Strategy 1: Try to extract content from markdown code blocks
    extracted = extract_code_content(text)
    if extracted and extracted != text:
        return extracted.strip()
    
    # Strategy 2: Remove all fence patterns
    t = text
    # Remove backtick fences with optional language identifier
    t = re.sub(r'```\w*\n?', '', t)
    t = re.sub(r'```', '', t)
    # Remove tilde fences
    t = re.sub(r'~~~\w*\n?', '', t)
    t = re.sub(r'~~~', '', t)
    # Remove any remaining single backticks
    t = t.replace('`', '')
    
    result = t.strip()
    
    # Validation: If result still has fences, try line-by-line cleaning
    if '```' in result or '~~~' in result:
        lines = result.split('\n')
        cleaned_lines = [ln for ln in lines if not ln.strip().startswith(('```', '~~~'))]
        result = '\n'.join(cleaned_lines).strip()
    
    return result


def extract_code_content(text: str) -> str:
    """
    Extract pure code content from markdown-wrapped text.
    Supports multiple markdown code block formats.
    """
    # Pattern 1: ```python\ncode\n```
    match = re.search(r'```(?:python|py)\s*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Pattern 2: ```\ncode\n```
    match = re.search(r'```\s*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Pattern 3: ~~~python\ncode\n~~~
    match = re.search(r'~~~(?:python|py)?\s*\n(.*?)~~~', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Pattern 4: Single backticks for inline code
    match = re.search(r'`([^`]+)`', text)
    if match and '\n' not in match.group(1):
        return match.group(1).strip()
    
    # No markdown found, return original
    return text


def cut_at_stops(text: str, stops: list[str]) -> str:
    """Cut text at first occurrence of any stop sequence."""
    if not stops:
        return text
    
    idxs = [text.find(s) for s in stops if text.find(s) >= 0]
    if not idxs:
        return text
    
    cut_point = min(idxs)
    return text[:cut_point]


def last_line_indent(prefix: str) -> int:
    if not prefix:
        return 0
    last = prefix.splitlines()[-1]
    return len(last) - len(last.lstrip(" "))


def align_first_line(prefix: str, completion: str) -> str:
    """
    Align the first line of completion with the indentation of the last line in prefix.
    
    KEY INSIGHT: If prefix ends with whitespace (indent), completion should start WITHOUT indent.
    If prefix ends with non-whitespace, completion needs proper indentation.
    
    Example 1:
      prefix = "def add(a, b):\n    "  # ends with 4 spaces
      completion = "return a + b"       # no indent needed
      → "return a + b" (correct)
    
    Example 2:
      prefix = "def add(a, b):"  # ends with colon
      completion = "return a + b"
      → "    return a + b" (need 4 spaces)
    """
    if not completion:
        return completion
    
    lines = completion.splitlines()
    if not lines:
        return completion
    
    # Check if prefix ends with whitespace (indent already provided)
    prefix_ends_with_indent = prefix and prefix[-1] in (' ', '\t')
    
    # Calculate base indentation from last line of prefix
    base = last_line_indent(prefix)
    
    fixed: list[str] = []
    first_line_original_indent = None
    
    for i, ln in enumerate(lines):
        # Empty lines pass through unchanged
        if not ln.strip():
            fixed.append(ln)
            continue
        
        if i == 0:
            # First line handling
            current_indent = len(ln) - len(ln.lstrip())
            content = ln.lstrip()
            
            if prefix_ends_with_indent:
                # Prefix already has indent, don't add more
                # But strip any indent model added
                fixed.append(content)
                first_line_original_indent = 0  # Track that first line has no indent
            else:
                # Prefix doesn't end with indent, add base indentation
                fixed.append((" " * base) + content)
                first_line_original_indent = base
        else:
            # Subsequent lines: preserve relative indentation
            current_indent = len(ln) - len(ln.lstrip())
            content = ln.lstrip()
            
            # If line had indentation in original, preserve it relative to first line
            if current_indent > 0:
                # Add first line indent + relative indent
                total_indent = first_line_original_indent + current_indent
                fixed.append((" " * total_indent) + content)
            else:
                # No relative indent, align with first line
                fixed.append((" " * first_line_original_indent) + content)
    
    return "\n".join(fixed)


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
    max_check = min(len(tail), len(completion), 128)  # Increased from implicit 256 to 128 for performance
    
    for k in range(max_check, 0, -1):
        if tail.endswith(completion[:k]):
            # Found overlap of length k, remove it from completion
            return completion[k:]
    
    return completion


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


def postprocess(prefix: str, suffix: str, raw: str, stops: list[str]) -> str:
    t = strip_fences(raw)
    t = cut_at_stops(t, stops)
    t = cut_overlap_tail(prefix, t)
    t = cut_overlap_head(suffix, t)
    t = align_first_line(prefix, t)
    return t.rstrip()
