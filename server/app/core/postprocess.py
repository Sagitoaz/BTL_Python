import re
from typing import List

FENCES = ("```python", "```py", "```", "~~~")

def strip_fences(text: str) -> str:
    t = text.strip()
    for fence in FENCES:
        t = re.sub(rf"{re.escape(fence)}", "", t, flags=re.IGNORECASE)
    t = re.sub(r"```.*?```", "", t, flags=re.DOTALL)
    t = re.sub(r"~~~.*?~~~", "", t, flags=re.DOTALL)
    return t.strip()

def cut_at_stops(text: str, stops: List[str]) -> str:
    idxs = [i for s in (stops or []) if (i := text.find(s)) >= 0]
    return text if not idxs else text[:min(idxs)]

def last_line_indent(prefix: str) -> int:
    if not prefix: return 0
    last = prefix.splitlines()[-1]
    return len(last) - len(last.lstrip(" "))

def normalize_indent(prefix: str, completion: str) -> str:
    base = last_line_indent(prefix)
    lines = completion.splitlines()
    fixed = []
    for i, ln in enumerate(lines):
        if not ln.strip():
            fixed.append(ln); continue
        fixed.append(((" " * base) + ln.lstrip()) if i == 0 else ln)
    return "\n".join(fixed)

def dedupe_with_prefix(prefix: str, completion: str, max_check: int = 120) -> str:
    tail = prefix[-max_check:] if prefix else ""
    cut = 0
    for k in range(min(len(tail), len(completion)), 0, -1):
        if tail.endswith(completion[:k]):
            cut = k; break
    return completion[cut:]

def dedupe_with_suffix(completion: str, suffix: str, max_check: int = 120) -> str:
    head = suffix[:max_check] if suffix else ""
    cut = 0
    for k in range(min(len(head), len(completion)), 0, -1):
        if completion.endswith(head[:k]):
            cut = k; break
    return completion[:-cut] if cut > 0 else completion

def postprocess(prefix: str, suffix: str, raw: str, stops: List[str]) -> str:
    t = strip_fences(raw)
    t = cut_at_stops(t, stops)
    t = normalize_indent(prefix, t)
    t = dedupe_with_prefix(prefix, t)
    t = dedupe_with_suffix(t, suffix)
    return t.rstrip()
