FENCES = ("```python", "```py", "```", "~~~")


def strip_fences(text: str) -> str:
    t = text
    for fence in FENCES:
        if fence in t:
            t = t.replace(fence, "")
    return t.strip()


def cut_at_stops(text: str, stops: list[str]) -> str:
    idxs = [i for s in (stops or []) if (i := text.find(s)) >= 0]
    return text if not idxs else text[: min(idxs)]


def last_line_indent(prefix: str) -> int:
    if not prefix:
        return 0
    last = prefix.splitlines()[-1]
    return len(last) - len(last.lstrip(" "))


def align_first_line(prefix: str, completion: str) -> str:
    base = last_line_indent(prefix)
    lines = completion.splitlines()
    fixed: list[str] = []
    for i, ln in enumerate(lines):
        if not ln.strip():
            fixed.append(ln)
            continue
        fixed.append(((" " * base) + ln.lstrip()) if i == 0 else ln)
    return "\n".join(fixed)


def cut_overlap_tail(prefix: str, completion: str) -> str:
    tail = prefix[-256:]
    cut = 0
    for k in range(min(len(tail), len(completion)), 0, -1):
        if tail.endswith(completion[:k]):
            cut = k
            break
    return completion[cut:]


def cut_overlap_head(suffix: str, completion: str) -> str:
    head = suffix[:256]
    cut = 0
    for k in range(min(len(head), len(completion)), 0, -1):
        if completion.endswith(head[:k]):
            cut = k
            break
    return completion[:-cut] if cut > 0 else completion


def postprocess(prefix: str, suffix: str, raw: str, stops: list[str]) -> str:
    t = strip_fences(raw)
    t = cut_at_stops(t, stops)
    t = cut_overlap_tail(prefix, t)
    t = cut_overlap_head(suffix, t)
    t = align_first_line(prefix, t)
    return t.rstrip()
