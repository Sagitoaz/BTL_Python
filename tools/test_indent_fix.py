"""
Unit tests for indentation fix in postprocess.py
"""
import sys
sys.path.insert(0, '/home/sagito/Desktop/BTL_Python/server')

from app.core.postprocess import align_first_line, postprocess


def test_no_extra_indent():
    """Model returns correctly indented code - should not add extra spaces"""
    prefix = "def add(a, b):\n    "
    completion = "return a + b"
    
    result = align_first_line(prefix, completion)
    print(f"Test 1: No extra indent")
    print(f"  Input: '{completion}'")
    print(f"  Output: '{result}'")
    
    # Should keep as-is (no indent on first line since prefix ends with indent)
    assert result == "return a + b", f"Expected 'return a + b', got '{result}'"
    print("  ✅ PASS\n")


def test_multi_line_with_else():
    """Multi-line completion with else block"""
    prefix = "def fibonacci(n):\n    if n <= 1:\n        return n\n    "
    completion = "else:\n    return fibonacci(n-1) + fibonacci(n-2)"
    
    result = align_first_line(prefix, completion)
    print(f"Test 2: Multi-line with else")
    print(f"  Input: {repr(completion)}")
    print(f"  Output: {repr(result)}")
    
    # First line should be "else:" (no extra indent)
    # Second line should be "    return..." (4 spaces relative to else)
    lines = result.split('\n')
    assert lines[0] == "else:", f"Expected 'else:', got '{lines[0]}'"
    assert lines[1] == "    return fibonacci(n-1) + fibonacci(n-2)", f"Expected '    return...', got '{lines[1]}'"
    print("  ✅ PASS\n")


def test_class_method_indent():
    """Class method with 8-space indent"""
    prefix = "class Calculator:\n    def divide(self, a, b):\n        "
    completion = "if b == 0:\n    raise ValueError('Division by zero')\nreturn a / b"
    
    result = align_first_line(prefix, completion)
    print(f"Test 3: Class method indent")
    print(f"  Input: {repr(completion)}")
    print(f"  Output: {repr(result)}")
    
    lines = result.split('\n')
    # First line: should have no extra indent (model provided it)
    assert lines[0] == "if b == 0:", f"Expected 'if b == 0:', got '{lines[0]}'"
    # Second line: should be indented relative to if
    assert lines[1] == "    raise ValueError('Division by zero')", f"Expected '    raise...', got '{lines[1]}'"
    # Third line: back to base level
    assert lines[2] == "return a / b", f"Expected 'return a / b', got '{lines[2]}'"
    print("  ✅ PASS\n")


def test_full_postprocess_pipeline():
    """Test complete postprocess pipeline"""
    prefix = "def add(a, b):\n    "
    suffix = "\n\ndef multiply(x, y):"
    raw = "    return a + b"  # Model returned with extra indent
    stops = ["\n\n```", "\n\n##"]
    
    result = postprocess(prefix, suffix, raw, stops)
    print(f"Test 4: Full pipeline")
    print(f"  Prefix: {repr(prefix)}")
    print(f"  Raw: {repr(raw)}")
    print(f"  Result: {repr(result)}")
    
    # Should strip the extra indent
    assert result == "return a + b", f"Expected 'return a + b', got '{result}'"
    print("  ✅ PASS\n")


def test_model_with_correct_indent():
    """Model returns code with correct relative indentation"""
    prefix = "def func():\n    "
    # Model returns properly indented multi-line code
    completion = "if True:\n    print('hello')\n    print('world')"
    
    result = align_first_line(prefix, completion)
    print(f"Test 5: Model with correct indent")
    print(f"  Input: {repr(completion)}")
    print(f"  Output: {repr(result)}")
    
    lines = result.split('\n')
    assert lines[0] == "if True:", f"Expected 'if True:', got '{lines[0]}'"
    assert lines[1] == "    print('hello')", f"Expected '    print('hello')', got '{lines[1]}'"
    assert lines[2] == "    print('world')", f"Expected '    print('world')', got '{lines[2]}'"
    print("  ✅ PASS\n")


if __name__ == "__main__":
    print("="*60)
    print("🧪 TESTING INDENTATION FIX")
    print("="*60 + "\n")
    
    try:
        test_no_extra_indent()
        test_multi_line_with_else()
        test_class_method_indent()
        test_full_postprocess_pipeline()
        test_model_with_correct_indent()
        
        print("="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
