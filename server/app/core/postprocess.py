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
    Preserve relative indentation for multi-line completions.
    
    LIMITATIONS: Python dedent keywords (elif, else, except, finally) are not automatically
    handled. Users should manually position cursor at the correct indentation level.
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
    
    # Find the minimum indentation in completion (excluding empty lines)
    min_indent = float('inf')
    for ln in lines:
        if ln.strip():  # Non-empty line
            indent = len(ln) - len(ln.lstrip())
            min_indent = min(min_indent, indent)
    
    if min_indent == float('inf'):
        min_indent = 0
    
    fixed: list[str] = []
    first_line_target_indent = 0
    
    for i, ln in enumerate(lines):
        # Empty lines pass through unchanged
        if ln.strip() == "":
            fixed.append("")
            continue
        
        # Calculate current indent and content
        current_indent = len(ln) - len(ln.lstrip())
        content = ln.lstrip()
        relative_indent = current_indent - min_indent
        
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
        else:
            # Subsequent lines: preserve relative indentation from first line
            # They start at column 0 (after newline), so need absolute indent
            fixed.append((" " * (first_line_target_indent + relative_indent)) + content)
    
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
