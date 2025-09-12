import re
import json
from collections import Counter
import uuid
from fastapi import HTTPException
from app.core.config import settings
from app.core.http import SESSION, TIMEOUT

# Indent helpers
# Mục tiêu:
# - Tự động “mồi” (prime) phần prefix trước khi gửi cho model: nếu dòng cuối cùng
#   (có nội dung) kết thúc bằng dấu ':' thì đó là một “block opener” của Python
#   (if/for/while/def/class/try/except/finally/with...). Sau dấu ':' thì dòng tiếp theo
#   PHẢI thụt vào một mức indent so với dòng đó.
# - Ta sẽ tự chèn '\n' + đúng chuỗi indent (TAB hoặc N spaces) vào cuối prefix,
#   để model “thấy” ngữ cảnh thụt dòng chuẩn và viết tiếp đúng vào lòng block.
#
# Thiết kế:
# - Không cố parse AST (nặng & dễ lỗi), chỉ dùng heuristics đủ tốt cho code completion.
# - Suy ra “đơn vị indent” (1 TAB hay 2/4/… spaces) từ các dòng trước đó trong prefix.
# - Bảo toàn style xuống dòng: nếu prefix dùng CRLF ('\r\n') thì kết quả vẫn trả CRLF.
#
# Edge cases đã tính:
# - File chỉ có spaces (2/4/8) → suy ra step phổ biến từ chênh lệch indent giữa các dòng.
# - File dùng TAB → phát hiện có TAB trong indent, trả về '\t' làm đơn vị indent.
# - Prefix kết thúc chưa có newline → thêm '\n' trước khi dán indent, để con trỏ đúng vị trí.
# - Prefix rỗng / không có dòng “có nội dung” → fallback indent = 4 spaces.
#
# Có thể tùy chỉnh: mặc định TAB = '\t', step spaces fallback = 4.
# Regex bắt chuỗi whitespace (space hoặc tab) đứng đầu dòng.
# Lưu ý: không dùng \s vì \s cũng match \r, \n; ta chỉ muốn [space/tab].
_WS = re.compile(r'^[ \t]*')

def _leading_ws(s: str) -> str:
    
    # Trả về chuỗi whitespace đứng đầu dòng s (VD: '', '    ', '\t\t', '  \t ').
    # Không đụng đến phần còn lại của dòng.
    
    m = _WS.match(s)
    return m.group(0) if m else ""  # nếu không match thì đầu dòng không có whitespace

def _uses_tab(lines: list[str]) -> bool:
    
    # Cho biết file (hoặc đoạn prefix) có đang dùng TAB để thụt dòng hay không.
    # Chiến lược: chỉ cần GẶP ít nhất một dòng có indent chứa '\t' là coi như “dùng TAB”.
    
    for l in lines:
        if not l.strip():  # bỏ qua dòng toàn whitespace (trống)
            continue
        if '\t' in _leading_ws(l):  # indent có tab?
            return True
    return False

def _space_width(s: str) -> int:
    
    # Đo “độ rộng” indent của một dòng khi quy ước TAB = 4 spaces (chỉ để ước lượng).
    # Ví dụ: indent '\t ' -> coi như '    ' + ' ' => 5.
    # Dùng cho việc suy ra step indent phổ biến trong file dùng spaces.
    
    indent = _leading_ws(s)
    return len(indent.replace('\t', '    '))

def _infer_indent_unit(text: str) -> str:
    
    # Suy ra “đơn vị indent” cho *một cấp độ*:
    #   - Nếu phát hiện có TAB trong indent → trả về '\t'.
    #   - Ngược lại, tính chênh lệch indent giữa các dòng liên tiếp (theo “độ rộng” quy đổi),
    #     chọn “bước tăng dương” phổ biến nhất làm step. Nếu không suy ra được → fallback = 4 spaces.

    # Trả về:
    #   - '\t'                (nếu dùng TAB)
    #   - ' ' * step (step∈[2..8])  (nếu dùng spaces)
    
    # Chuẩn hoá newline về LF để dễ split; ta sẽ khôi phục CRLF về sau nếu cần.
    norm = text.replace('\r\n', '\n')
    # Chỉ xét các dòng “có nội dung” để tránh nhiễu từ dòng trống.
    lines = [l for l in norm.split('\n') if l.strip()]

    # Trường hợp prefix rỗng / toàn dòng trống → mặc định 4 spaces
    if not lines:
        return ' ' * 4

    # Nếu bất kỳ dòng nào dùng TAB trong indent → ưu tiên TAB
    if _uses_tab(lines):
        return '\t'

    # Tính “độ rộng” indent (TAB quy ước = 4) cho từng dòng
    widths = [_space_width(l) for l in lines]

    # Xem giữa các dòng liên tiếp, độ tăng indent dương là bao nhiêu
    diffs = [b - a for a, b in zip(widths, widths[1:]) if b > a]

    # Nếu có dữ liệu -> lấy step phổ biến nhất; nếu không -> fallback
    if diffs:
        # Ví dụ: diffs = [4, 4, 2, 4] -> Counter chọn 4
        step = Counter(diffs).most_common(1)[0][0]
        # Kẹp step trong khoảng an toàn để tránh mấy trường hợp lố (VD: 16 do copy/paste)
        step = max(2, min(step, 8))
        return ' ' * step

    # Không suy ra được step (ví dụ file toàn 1 level indent hoặc flat)
    return ' ' * 4

def _find_last_nonempty_line(lines: list[str]) -> tuple[int, str]:
    
    # Trả về (index, nội dung) của dòng “có nội dung” cuối cùng trong một danh sách dòng.
    # Nếu không có dòng nào có nội dung -> (-1, "").
    
    i = len(lines) - 1
    while i >= 0:
        if lines[i].strip():  # có ký tự không phải whitespace?
            return i, lines[i]
        i -= 1
    return -1, ""

def _prime_prefix_with_indent(prefix: str) -> str:
    
    # Mồi indent sau dấu ':'.
    # - Nếu đuôi prefix đã ở dòng mới và chỉ có whitespace -> GHI ĐÈ whitespace bằng indent đúng.
    # - Nếu đuôi prefix chưa xuống dòng -> thêm '\n' + indent.
    # - Nếu dòng cuối có nội dung không kết thúc ':' -> trả y nguyên.
    # Bảo toàn CRLF.
    
    if not prefix:
        return prefix

    uses_crlf = '\r\n' in prefix
    p = prefix.replace('\r\n', '\n')

    lines = p.split('\n')
    idx, last = _find_last_nonempty_line(lines)
    if idx == -1 or not last.rstrip().endswith(':'):
        return prefix  # không mở block

    base = _leading_ws(last)
    unit = _infer_indent_unit(p)
    need = base + unit

    # tách phần "đuôi" sau newline cuối cùng
    nl_pos = p.rfind('\n')
    tail = p[nl_pos + 1:] if nl_pos != -1 else p

    if nl_pos != -1 and tail.strip() == "":
        # Đang ở dòng mới và chỉ có whitespace -> ghi đè bằng indent đúng
        p = p[:nl_pos + 1] + need
    else:
        # Chưa ở dòng mới (hoặc tail có ký tự khác whitespace) -> thêm newline + indent
        if not p.endswith('\n'):
            p += '\n'
        p += need

    return p.replace('\n', '\r\n') if uses_crlf else p


# Prompt builder

def build_prompt(prefix: str, suffix: str, language: str) -> str:
    
    # Prompt FIM, ép code-only cho Python (language được giữ để không phá chữ ký).
    # Có 'prime indent' để dòng đầu tiên vào đúng mức thụt nếu trước đó là ':'.
    
    # chuẩn hoá newline và prime indent
    prefix2 = _prime_prefix_with_indent(prefix)

    rules = [
        "Return ONLY the missing Python code.",
        "Never output backticks or any Markdown.",
        "Do not add explanations, comments, or docstrings unless strictly required for correctness.",
        "Respect indentation from the last line before the cursor.",
        "Do not repeat any code that already exists in the prefix or suffix.",
        "Prefer the shortest syntactically valid completion; close any open blocks/brackets.",
        "Stop at a natural boundary (end of statement/block).",
    ]

    return (
        "You are a Python code completion engine.\n"
        "Follow ALL rules strictly.\n"
        "Rules:\n- " + "\n- ".join(rules) + "\n"
        "Complete at the cursor using the surrounding context.\n"
        "---\n"
        f"<prefix>\n{prefix2}\n</prefix>\n"
        f"<suffix>\n{suffix}\n</suffix>\n"
        "<cursor/>\n"
    )

# Ollama caller

def call_generate(prompt: str, max_tokens: int, temperature: float, stop, stream: bool):
    body = {
        "model": settings.MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_ctx": 2048,
            "num_predict": max_tokens,
            "repeat_penalty": 1.1,
            "stop": stop,
        },
    }
    # Nếu settings.OLLAMA_URL là base (vd http://127.0.0.1:11434) thì
    # cân nhắc đổi thành ... + "/api/generate". Nếu đã là endpoint đầy đủ thì giữ nguyên.
    url = f"{settings.OLLAMA_URL}"
    resp = SESSION.post(url, json=body, timeout=TIMEOUT, stream=stream)
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=502, detail={"ollama_error": detail})
    return resp

def new_request_id() -> str:
    return str(uuid.uuid4())[:8]
