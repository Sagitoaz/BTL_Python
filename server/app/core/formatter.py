"""
Code formatter integration for auto-formatting completions.
Supports black (Python), prettier (JavaScript/TypeScript), and clang-format (C++).
"""
import subprocess
import tempfile
import os
from typing import Optional, Literal


def format_python_code(code: str, line_length: int = 88) -> tuple[str, Optional[str]]:
    """
    Format Python code using black.
    Returns (formatted_code, error_message).
    If formatting fails, returns original code with error message.
    """
    try:
        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # Run black on the temp file
            result = subprocess.run(
                ['black', '--quiet', '--line-length', str(line_length), temp_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Read formatted code
                with open(temp_path, 'r') as f:
                    formatted = f.read()
                return formatted, None
            else:
                error = result.stderr or "Black formatting failed"
                return code, error
                
        finally:
            # Clean up temp file
            os.unlink(temp_path)
            
    except FileNotFoundError:
        return code, "black not installed (pip install black)"
    except subprocess.TimeoutExpired:
        return code, "Black formatting timeout"
    except Exception as e:
        return code, f"Formatting error: {str(e)}"


def format_with_autopep8(code: str, max_line_length: int = 88) -> tuple[str, Optional[str]]:
    """
    Format Python code using autopep8 (less aggressive than black).
    Returns (formatted_code, error_message).
    """
    try:
        result = subprocess.run(
            ['autopep8', '--max-line-length', str(max_line_length), '-'],
            input=code,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return result.stdout, None
        else:
            return code, result.stderr or "autopep8 failed"
            
    except FileNotFoundError:
        return code, "autopep8 not installed (pip install autopep8)"
    except subprocess.TimeoutExpired:
        return code, "autopep8 timeout"
    except Exception as e:
        return code, f"Formatting error: {str(e)}"


def normalize_python_code(code: str) -> str:
    """
    Lightweight normalization for Python code when a proper formatter
    is not available or fails.

    - Convert tabs to 4 spaces
    - Strip trailing whitespace
    - Collapse multiple blank lines to a single blank line
    - Ensure consistent newline endings (\n)
    - Remove leading/trailing blank lines
    """
    if not code:
        return code

    # Normalize newlines
    text = code.replace('\r\n', '\n').replace('\r', '\n')

    # Replace tabs with 4 spaces
    text = text.replace('\t', ' ' * 4)

    # Strip trailing spaces on each line
    lines = [ln.rstrip() for ln in text.split('\n')]

    # Collapse multiple blank lines
    new_lines: list[str] = []
    blank = False
    for ln in lines:
        if ln == "":
            if not blank:
                new_lines.append("")
            blank = True
        else:
            new_lines.append(ln)
            blank = False

    # Remove leading/trailing blank lines
    while new_lines and new_lines[0] == "":
        new_lines.pop(0)
    while new_lines and new_lines[-1] == "":
        new_lines.pop()

    return "\n".join(new_lines)


def format_cpp_code(code: str) -> tuple[str, Optional[str]]:
    """
    Format C++ code using clang-format.
    Returns (formatted_code, error_message).
    If formatting fails, returns original code with error message.
    """
    try:
        result = subprocess.run(
            ['clang-format', '--style=LLVM'],
            input=code,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return result.stdout, None
        else:
            return code, result.stderr or "clang-format failed"
            
    except FileNotFoundError:
        return code, "clang-format not installed"
    except subprocess.TimeoutExpired:
        return code, "clang-format timeout"
    except Exception as e:
        return code, f"Formatting error: {str(e)}"


def normalize_cpp_code(code: str) -> str:
    """
    Lightweight normalization for C++ code when clang-format is not available.
    
    - Convert tabs to 2 spaces (C++ convention)
    - Strip trailing whitespace
    - Normalize newlines
    """
    if not code:
        return code
    
    # Normalize newlines
    text = code.replace('\r\n', '\n').replace('\r', '\n')
    
    # Replace tabs with 2 spaces (C++ convention)
    text = text.replace('\t', '  ')
    
    # Strip trailing spaces on each line
    lines = [ln.rstrip() for ln in text.split('\n')]
    
    # Remove leading/trailing blank lines
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    
    return "\n".join(lines)


def format_code(
    code: str,
    language: Literal["python", "javascript", "typescript", "cpp", "c++", "c", ""] = "python",
    formatter: Literal["black", "autopep8", "prettier", "clang-format", "auto"] = "auto"
) -> tuple[str, Optional[str]]:
    """
    Auto-format code based on language.
    
    Args:
        code: The code to format
        language: Programming language
        formatter: Which formatter to use ("auto" = choose best for language)
    
    Returns:
        (formatted_code, error_message)
        If formatting fails, returns original code with error message.
    """
    if not code.strip():
        return code, None
    
    # Auto-select formatter based on language
    if formatter == "auto":
        if language == "python":
            formatter = "black"
        elif language in ("javascript", "typescript"):
            formatter = "prettier"
        elif language in ("cpp", "c++", "c"):
            formatter = "clang-format"
        else:
            return code, None  # No formatter for this language
    
    # Apply formatter
    if formatter == "black":
        return format_python_code(code)
    elif formatter == "autopep8":
        return format_with_autopep8(code)
    elif formatter == "clang-format":
        return format_cpp_code(code)
    elif formatter == "prettier":
        return code, "prettier not yet implemented"
    else:
        return code, f"Unknown formatter: {formatter}"


def should_format(code: str, language: str) -> bool:
    """
    Decide if code should be formatted.
    Skip formatting for very short completions or non-code.
    """
    # Skip empty or very short code
    if len(code.strip()) < 10:
        return False
    
    # Skip if not a supported language
    if language not in ("python", "javascript", "typescript", "cpp", "c++", "c"):
        return False
    
    # Skip if it's just a single expression
    if '\n' not in code and len(code) < 50:
        return False
    
    return True


# Example usage
if __name__ == "__main__":
    test_code = """
def fibonacci(n):
    if n<=1:return n
    return fibonacci(n-1)+fibonacci(n-2)
"""
    
    print("Original code:")
    print(test_code)
    print("\nFormatted with black:")
    formatted, error = format_python_code(test_code.strip())
    if error:
        print(f"Error: {error}")
    else:
        print(formatted)
    
    print("\nFormatted with autopep8:")
    formatted2, error2 = format_with_autopep8(test_code.strip())
    if error2:
        print(f"Error: {error2}")
    else:
        print(formatted2)
