"""
Groq API service for code completion.
Replaces Ollama with Groq Cloud - faster, free, and always available.
"""
import logging
from typing import Optional
import uuid

from fastapi import HTTPException
import requests

from app.core.config import settings
from app.schemas.completion import CompleteRequest

logger = logging.getLogger(__name__)


def build_prompt(seq: CompleteRequest) -> str:
    """
    Build an enhanced prompt with clear instructions and few-shot examples.
    Optimized for Groq's fast inference.
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
    
    # Few-shot examples
    examples = f"""
EXAMPLE 1 - Function body:
<prefix>def add(a, b):\n    </prefix>
<suffix>\n\ndef multiply(x, y):</suffix>
OUTPUT: return a + b

EXAMPLE 2 - Continue statement:
<prefix>if user.is_authenticated:\n    </prefix>
<suffix>\nelse:\n    return redirect('/login')</suffix>
OUTPUT: return render_template('dashboard.html')

EXAMPLE 3 - List comprehension:
<prefix>numbers = [1, 2, 3, 4, 5]\nsquares = [</prefix>
<suffix>]\nprint(squares)</suffix>
OUTPUT: x**2 for x in numbers
"""
    
    return (
        f"You are an expert {seq.language} code completion AI.\n"
        "Your ONLY job is to complete the code at the cursor position.\n\n"
        "RULES (follow ALL strictly):\n- " + "\n- ".join(rules) + "\n\n"
        + examples + "\n"
        "NOW complete the following code at <cursor/> position:\n\n"
        f"<prefix>\n{seq.prefix}\n</prefix>\n\n"
        f"<suffix>\n{seq.suffix}\n</suffix>\n\n"
        "<cursor/>\n\n"
        "OUTPUT (raw code only, NO markdown):\n"
    )


def call_groq_completion(
    prompt: str, 
    max_tokens: int, 
    temperature: float,
    stop: Optional[list[str]] = None
) -> str:
    """
    Call Groq API for code completion.
    Returns the raw completion text.
    """
    if not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY not configured"
        )
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Groq uses OpenAI-compatible API
    # Limit stop sequences to max 4 (Groq requirement)
    stop_sequences = (stop or [])[:4] if stop else []
    
    body = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a code completion assistant. Return only the code that should appear at the cursor, without any markdown formatting or explanations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stop": stop_sequences,
        "stream": False
    }
    
    try:
        logger.info(f"Calling Groq API with model {settings.GROQ_MODEL}")
        resp = requests.post(
            url, 
            headers=headers, 
            json=body, 
            timeout=settings.TIMEOUT_SECONDS
        )
        
        if resp.status_code >= 400:
            error_detail = resp.text[:500]
            logger.error(f"Groq API error {resp.status_code}: {error_detail}")
            raise HTTPException(
                status_code=502,
                detail={"groq_error": error_detail}
            )
        
        data = resp.json()
        completion = data["choices"][0]["message"]["content"]
        
        logger.info(f"Groq completion received: {len(completion)} chars")
        return completion
        
    except requests.exceptions.RequestException as e:
        logger.exception("Network error calling Groq API")
        raise HTTPException(
            status_code=502,
            detail={"groq_error": f"Network error: {str(e)}"}
        )
    except KeyError as e:
        logger.exception("Unexpected response format from Groq")
        raise HTTPException(
            status_code=502,
            detail={"groq_error": f"Invalid response format: {str(e)}"}
        )


def new_request_id() -> str:
    """Generate unique request ID."""
    return str(uuid.uuid4())[:8]
