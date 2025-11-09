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
    Enhanced FIM (Fill-In-the-Middle) prompt for high-quality code completion.
    Uses proven techniques from GitHub Copilot and CodeLlama.
    Supports comment-to-code generation.
    """
    
    # Check if this is comment-to-code generation
    is_comment_to_code = req.comment_instruction is not None and len(req.comment_instruction) > 0
    
    # Build context-aware system message
    if is_comment_to_code:
        system_msg = f"""You are an expert {req.language} code generator. Your task is to generate code based on the comment instruction.

CRITICAL RULES:
1. Read the comment instruction carefully: "{req.comment_instruction}"
2. Generate complete, working code that implements the instruction
3. Output ONLY code - NO explanations, NO markdown, NO backticks
4. The code must be syntactically correct and follow best practices
5. Match the existing code style (indentation, naming patterns)
6. Include necessary error handling and edge cases"""
    else:
        system_msg = f"""You are an expert {req.language} code completion engine. Your task is to complete code at the <FILL> position.

CRITICAL RULES:
1. Output ONLY the missing code - NO explanations, NO markdown, NO backticks
2. Match the existing code style EXACTLY (indentation, naming, patterns)
3. The completion must be syntactically correct and contextually appropriate
4. DO NOT repeat code from <PREFIX> or <SUFFIX>
5. Maintain proper indentation relative to surrounding code
6. Prefer concise, idiomatic solutions"""

    # Language-specific guidelines
    if req.language == "python":
        lang_rules = """
Python Guidelines:
- Use 4 spaces for indentation (never tabs)
- Follow PEP 8 naming: snake_case for functions/variables, PascalCase for classes
- After ':' (def, class, if, for, etc.), indent the next line by 4 spaces
- Prefer list/dict comprehensions over loops when readable
- Use type hints if the surrounding code uses them"""
    elif req.language in ["cpp", "c++", "c"]:
        lang_rules = """
C++ Guidelines:
- Match existing indentation (usually 2 or 4 spaces, or tabs)
- Include semicolons and proper braces {} placement
- Use 'auto' for complex types when appropriate
- Prefer range-based for loops: for (const auto& item : container)
- Use std:: prefix unless 'using namespace std' is in <PREFIX>
- Match existing naming convention (camelCase, snake_case, or PascalCase)"""
    else:
        lang_rules = ""
    
    # Add user personalization
    style_hints = f"\nUSER PREFERENCES: {user_style_hints}" if user_style_hints else ""
    
    # Few-shot examples with proper FIM format
    if req.language in ["cpp", "c++", "c"]:
        examples = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE 1 - Simple function completion:
<PREFIX>
int add(int a, int b) {
    
</PREFIX>
<SUFFIX>
}

int main() {
</SUFFIX>
<FILL>return a + b;</FILL>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE 2 - Loop with proper indentation:
<PREFIX>
void printArray(int arr[], int size) {
    for (int i = 0; i < size; i++) {
        
</PREFIX>
<SUFFIX>
    }
}
</SUFFIX>
<FILL>std::cout << arr[i] << " ";</FILL>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE 3 - Class method:
<PREFIX>
class Calculator {
public:
    int multiply(int a, int b) {
        
</PREFIX>
<SUFFIX>
    }
};
</SUFFIX>
<FILL>return a * b;</FILL>"""
    else:  # Python
        examples = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE 1 - Simple function completion:
<PREFIX>
def calculate_sum(numbers):
    
</PREFIX>
<SUFFIX>

result = calculate_sum([1, 2, 3])
</SUFFIX>
<FILL>if not numbers:
        return 0
    return sum(numbers)</FILL>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE 2 - Inline completion:
<PREFIX>
def is_even(n):
    return 
</PREFIX>
<SUFFIX>

def is_odd(n):
</SUFFIX>
<FILL>n % 2 == 0</FILL>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE 3 - List comprehension:
<PREFIX>
names = ['alice', 'bob', 'charlie']
uppercase_names = [
</PREFIX>
<SUFFIX>
]
print(uppercase_names)
</SUFFIX>
<FILL>name.upper() for name in names</FILL>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE 4 - Multi-line with proper indent:
<PREFIX>
class UserManager:
    def validate_user(self, user_id):
        
</PREFIX>
<SUFFIX>
        return is_valid
    
    def delete_user(self, user_id):
</SUFFIX>
<FILL>if not user_id:
            return False
        user = self.db.get_user(user_id)
        is_valid = user is not None and user.active</FILL>"""
    
    # Build final prompt with FIM structure
    prompt = f"""{system_msg}
{lang_rules}{style_hints}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEARN FROM THESE EXAMPLES:
{examples}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOW COMPLETE THIS CODE:

<PREFIX>
{req.prefix}
</PREFIX>

<SUFFIX>
{req.suffix}
</SUFFIX>

<FILL>"""
    
    return prompt


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
