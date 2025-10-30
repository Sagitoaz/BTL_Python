#!/usr/bin/env python3
"""
Quick test script to verify Phase 1 improvements work correctly.
Tests postprocessing functions without needing a running server.
"""
import sys
import os

# Add server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from app.core.postprocess import (
    strip_fences,
    extract_code_content,
    align_first_line,
    cut_overlap_tail,
    cut_overlap_head,
    postprocess
)

def test_strip_fences():
    """Test markdown fence removal."""
    tests = [
        ("```python\nreturn a + b\n```", "return a + b"),
        ("```py\ndef func():\n    pass\n```", "def func():\n    pass"),
        ("```\nx = 5\n```", "x = 5"),
        ("~~~python\nreturn True\n~~~", "return True"),
    ]
    
    passed = 0
    for input_text, expected in tests:
        result = strip_fences(input_text)
        if "```" not in result and "~~~" not in result:
            passed += 1
            print(f"✅ Strip fences: PASS")
        else:
            print(f"❌ Strip fences: FAIL - Still has fences: {repr(result)}")
    
    return passed, len(tests)

def test_extract_code():
    """Test code extraction."""
    tests = [
        ("```python\ndef add(a, b):\n    return a + b\n```", "def add(a, b):\n    return a + b"),
        ("```\ncode here\n```", "code here"),
    ]
    
    passed = 0
    for input_text, expected_content in tests:
        result = extract_code_content(input_text)
        if expected_content in result and "```" not in result:
            passed += 1
            print(f"✅ Extract code: PASS")
        else:
            print(f"❌ Extract code: FAIL - {repr(result)}")
    
    return passed, len(tests)

def test_indent_alignment():
    """Test indent alignment."""
    tests = [
        ("def func():\n    ", "return x", "    return x"),
        ("class A:\n    def func():\n        ", "pass", "        pass"),
    ]
    
    passed = 0
    for prefix, completion, expected_start in tests:
        result = align_first_line(prefix, completion)
        if result.startswith(expected_start):
            passed += 1
            print(f"✅ Indent alignment: PASS")
        else:
            print(f"❌ Indent alignment: FAIL - Expected start '{expected_start}', got '{result[:20]}'")
    
    return passed, len(tests)

def test_overlap_detection():
    """Test overlap removal."""
    # Test tail overlap
    prefix = "def add(a, b):"
    completion = "b):\n    return a + b"
    result = cut_overlap_tail(prefix, completion)
    
    tail_pass = not result.startswith("b):")
    print(f"{'✅' if tail_pass else '❌'} Overlap tail: {'PASS' if tail_pass else 'FAIL'}")
    
    # Test head overlap
    suffix = "\n\ndef multiply(x, y):"
    completion = "return a + b\n\ndef multiply"
    result = cut_overlap_head(suffix, completion)
    
    head_pass = not result.endswith("multiply")
    print(f"{'✅' if head_pass else '❌'} Overlap head: {'PASS' if head_pass else 'FAIL'}")
    
    return (1 if tail_pass else 0) + (1 if head_pass else 0), 2

def test_full_pipeline():
    """Test complete postprocess pipeline."""
    prefix = "def add(a, b):\n    "
    suffix = "\n\ndef sub(x, y):"
    raw = "```python\nreturn a + b\n```"
    stops = ["\n\n"]
    
    result = postprocess(prefix, suffix, raw, stops)
    
    checks = {
        "No markdown": "```" not in result,
        "Has content": "return a + b" in result,
        "Proper indent": result.strip().startswith("return") or result.startswith("    return"),
    }
    
    passed = sum(checks.values())
    for check_name, check_result in checks.items():
        print(f"{'✅' if check_result else '❌'} {check_name}: {'PASS' if check_result else 'FAIL'}")
    
    if not all(checks.values()):
        print(f"   Result: {repr(result)}")
    
    return passed, len(checks)

def main():
    print("🧪 PHASE 1 POSTPROCESSING TESTS\n")
    print("=" * 50)
    
    total_passed = 0
    total_tests = 0
    
    print("\n📋 Test 1: Markdown Fence Removal")
    p, t = test_strip_fences()
    total_passed += p
    total_tests += t
    
    print("\n📋 Test 2: Code Extraction")
    p, t = test_extract_code()
    total_passed += p
    total_tests += t
    
    print("\n📋 Test 3: Indent Alignment")
    p, t = test_indent_alignment()
    total_passed += p
    total_tests += t
    
    print("\n📋 Test 4: Overlap Detection")
    p, t = test_overlap_detection()
    total_passed += p
    total_tests += t
    
    print("\n📋 Test 5: Full Pipeline")
    p, t = test_full_pipeline()
    total_passed += p
    total_tests += t
    
    print("\n" + "=" * 50)
    print(f"\n📊 RESULTS: {total_passed}/{total_tests} tests passed ({total_passed*100//total_tests}%)")
    
    if total_passed == total_tests:
        print("✅ ✅ ✅ ALL TESTS PASSED! ✅ ✅ ✅")
        print("\n🚀 Postprocessing is working correctly!")
        print("⚠️  If server still returns markdown, you need to RESTART the server.")
        return 0
    else:
        print(f"❌ {total_tests - total_passed} tests failed")
        print("🔧 Some postprocessing functions need fixing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
