import uuid

from fastapi import HTTPException
import logging

from app.core.config import settings
from app.core.http import SESSION, TIMEOUT
from app.schemas.completion import CompleteRequest

logger = logging.getLogger(__name__)


def build_prompt(seq: CompleteRequest) -> str:
    """
    Build an enhanced prompt with clear instructions and few-shot examples.
    Emphasizes returning ONLY raw code without markdown formatting.
    """
    rules = [
        f"Return ONLY the missing {seq.language} code that should appear at the cursor position.",
        "CRITICAL: Never use markdown code blocks, backticks (```), or any formatting markers.",
        "Output must be pure, executable code that can be inserted directly into the file.",
        "Do not add explanations, comments, or docstrings unless they are part of the actual code logic.",
        "Respect the exact indentation from the last line before the cursor.",
        "Do not repeat any code that already exists in the prefix or suffix.",
        "If the prefix ends with ':', indent the completion by 4 spaces (Python block).",
        "Keep completions concise but complete - finish the current logical block.",
    ]
    
    # Few-shot examples to guide the model
    examples = f"""
EXAMPLE 1 - Function body completion:
<prefix>
def add(a, b):
    
</prefix>
<suffix>

def multiply(x, y):
</suffix>
CORRECT OUTPUT:
    return a + b

EXAMPLE 2 - Continue statement:
<prefix>
if user.is_authenticated:
    
</prefix>
<suffix>
else:
    return redirect('/login')
</suffix>
CORRECT OUTPUT:
    return render_template('dashboard.html')

EXAMPLE 3 - List comprehension:
<prefix>
numbers = [1, 2, 3, 4, 5]
squares = [
</prefix>
<suffix>
]
print(squares)
</suffix>
CORRECT OUTPUT:
x**2 for x in numbers

---
"""
    
    return (
        f"You are an expert {seq.language} code completion AI assistant.\n"
        "Your ONLY job is to complete the code at the cursor position.\n\n"
        "RULES (follow ALL strictly):\n- " + "\n- ".join(rules) + "\n\n"
        + examples +
        "NOW complete the following code at <cursor/> position:\n\n"
        f"<prefix>\n{seq.prefix}\n</prefix>\n\n"
        f"<suffix>\n{seq.suffix}\n</suffix>\n\n"
        "<cursor/>\n\n"
        "OUTPUT (raw code only, NO markdown):\n"
    )


def call_generate(prompt: str, max_tokens: int, temperature: float, stop, stream: bool):
    body = {
        "model": settings.MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": float(temperature),
            "num_ctx": getattr(settings, "NUM_CTX", 4096),  # Increased from 2048 to 4096
            "num_predict": int(max_tokens),
            "repeat_penalty": 1.1,
            "stop": stop,
            "top_p": 0.9,  # Add top_p for better quality
            "top_k": 40,   # Add top_k sampling
        },
    }
    # Build headers: if an Ollama API key is configured, attach Authorization header
    headers = {}
    if getattr(settings, "OLLAMA_API_KEY", None):
        # Ollama Cloud typically expects a Bearer token
        headers["Authorization"] = f"Bearer {settings.OLLAMA_API_KEY}"

    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/generate"
    try:
        resp = SESSION.post(url, json=body, timeout=TIMEOUT, stream=stream, headers=headers or None)
    except Exception as exc:  # network/connection errors
        logger.exception("Error while calling Ollama at %s", settings.OLLAMA_URL)
        raise HTTPException(status_code=502, detail={"ollama_error": str(exc)})
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=502, detail={"ollama_error": detail})
    return resp

# --- Public shim expected by tests ---
def generate_completion(*args, **kwargs) -> str:
    """
    Public entry expected by tests. If you already have an internal function that
    does the actual work (e.g., _generate_completion or complete_once), delegate to it.
    Otherwise this will raise until wired up — tests will monkeypatch it anyway.
    """
    try:
        # Nếu bạn đã có hàm thật, đổi tên ở đây cho đúng:
        return _generate_completion(*args, **kwargs)  # type: ignore[name-defined]
    except NameError:
        raise RuntimeError("generate_completion is not wired to an internal impl yet")


def new_request_id() -> str:
    return str(uuid.uuid4())[:8]
