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


def build_prompt(req: CompleteRequest, user_style_hints: str = "") -> str:
    """
    Build an enhanced prompt with clear instructions and few-shot examples.
    Optionally includes personalized style hints based on user's coding patterns.
    Optimized for Groq's fast inference.
    Supports multiple languages including Python and C++.
    """
    rules = [
        f"You are an expert {req.language} coding assistant. Complete the code at <cursor/> position.",
        "CRITICAL: Return ONLY executable code - NO markdown, NO backticks (```), NO explanations.",
        "Output must be pure code that can be inserted directly into the file.",
        "Analyze the prefix and suffix context carefully to understand the intent.",
        "Maintain consistent indentation - match the last line's indentation level.",
        "DO NOT repeat code that already exists in prefix or suffix.",
        "Prefer concise, idiomatic solutions over verbose code.",
    ]
    
    # Language-specific rules
    if req.language == "python":
        rules.append("Python: After ':' indent by 4 spaces. Use snake_case for variables/functions.")
        rules.append("Python: Prefer list comprehensions and built-in functions when appropriate.")
    elif req.language in ["cpp", "c++", "c"]:
        rules.append("C++: Include semicolons, proper braces, and type declarations.")
        rules.append("C++: Use C++ idioms: auto, range-based for, STL containers.")
        rules.append("C++: Prefer std:: prefix for standard library (unless 'using namespace std' in prefix).")
    
    # Add user style hints if available
    if user_style_hints:
        rules.append(f"USER STYLE PREFERENCES: {user_style_hints}")
    
    # Enhanced few-shot examples based on language
    if req.language in ["cpp", "c++", "c"]:
        examples = """
EXAMPLE 1 - Inline completion (C++):
<prefix>int factorial(int n) { return </prefix>
<suffix>; }</suffix>
OUTPUT: (n <= 1) ? 1 : n * factorial(n - 1)

EXAMPLE 2 - Multi-line function (C++):
<prefix>void printVector(const std::vector<int>& vec) {
    </prefix>
<suffix>
}

int main()</suffix>
OUTPUT: for (const auto& val : vec) {
        std::cout << val << " ";
    }
    std::cout << std::endl;

EXAMPLE 3 - Class method (C++):
<prefix>class Calculator {
public:
    int add(int a, int b) {
        </prefix>
<suffix>
    }
};</suffix>
OUTPUT: return a + b;
"""
    else:  # Python
        examples = """
EXAMPLE 1 - Inline completion (Python):
<prefix>def is_even(n): return </prefix>
<suffix>

def is_odd(n):</suffix>
OUTPUT: n % 2 == 0

EXAMPLE 2 - Multi-line function (Python):
<prefix>def find_max(numbers):
    </prefix>
<suffix>

result = find_max([1, 5, 3])</suffix>
OUTPUT: if not numbers:
        return None
    return max(numbers)

EXAMPLE 3 - List comprehension (Python):
<prefix>fruits = ['apple', 'banana', 'cherry']
uppercase = [</prefix>
<suffix>]
print(uppercase)</suffix>
OUTPUT: f.upper() for f in fruits
"""
    
    # Build final prompt with enhanced context
    return (
        f"You are an expert {req.language} code completion AI.\n"
        "Task: Complete code at <cursor/> position using surrounding context.\n\n"
        "STRICT RULES:\n" + "\n".join(f"- {r}" for r in rules) + "\n\n"
        "EXAMPLES (learn the pattern):\n" + examples + "\n"
        "═══════════════════════════════════════\n"
        "NOW COMPLETE THIS CODE:\n\n"
        f"<prefix>\n{req.prefix}\n</prefix>\n\n"
        f"<suffix>\n{req.suffix}\n</suffix>\n\n"
        "<cursor/>\n\n"
        "YOUR COMPLETION (raw code only):\n"
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
