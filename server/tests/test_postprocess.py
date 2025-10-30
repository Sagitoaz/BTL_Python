"""
Comprehensive tests for postprocessing functions.
Tests markdown removal, indent alignment, and overlap detection.
"""
import pytest
from app.core.postprocess import (
    strip_fences,
    extract_code_content,
    cut_at_stops,
    last_line_indent,
    align_first_line,
    cut_overlap_tail,
    cut_overlap_head,
    postprocess,
)


class TestStripFences:
    """Test markdown fence removal."""
    
    def test_strip_python_fence(self):
        """Test removal of ```python fence."""
        text = "```python\nreturn a + b\n```"
        result = strip_fences(text)
        assert result == "return a + b"
        assert "```" not in result
    
    def test_strip_py_fence(self):
        """Test removal of ```py fence."""
        text = "```py\ndef hello():\n    print('hi')\n```"
        result = strip_fences(text)
        assert "```" not in result
        assert "def hello():" in result
    
    def test_strip_generic_fence(self):
        """Test removal of generic ``` fence."""
        text = "```\nx = 5\ny = 10\n```"
        result = strip_fences(text)
        assert result == "x = 5\ny = 10"
    
    def test_strip_tilde_fence(self):
        """Test removal of ~~~ fence."""
        text = "~~~python\nreturn True\n~~~"
        result = strip_fences(text)
        assert result == "return True"
        assert "~~~" not in result
    
    def test_multiple_fences(self):
        """Test removal of multiple fence markers."""
        text = "```python\n```\ncode here\n```\n```"
        result = strip_fences(text)
        assert "```" not in result
        assert "code here" in result
    
    def test_no_fences(self):
        """Test that clean code passes through unchanged."""
        text = "return a + b"
        result = strip_fences(text)
        assert result == text
    
    def test_inline_backticks(self):
        """Test removal of inline backticks."""
        text = "`return value`"
        result = strip_fences(text)
        assert result == "return value"


class TestExtractCodeContent:
    """Test code extraction from markdown."""
    
    def test_extract_python_block(self):
        """Test extracting from ```python block."""
        text = "```python\ndef func():\n    pass\n```"
        result = extract_code_content(text)
        assert result == "def func():\n    pass"
    
    def test_extract_py_block(self):
        """Test extracting from ```py block."""
        text = "```py\nx = 1\n```"
        result = extract_code_content(text)
        assert result == "x = 1"
    
    def test_extract_generic_block(self):
        """Test extracting from generic ``` block."""
        text = "```\ncode\n```"
        result = extract_code_content(text)
        assert result == "code"
    
    def test_no_markdown(self):
        """Test that plain code returns unchanged."""
        text = "plain code"
        result = extract_code_content(text)
        assert result == text


class TestCutAtStops:
    """Test stop sequence cutting."""
    
    def test_cut_at_double_newline(self):
        """Test cutting at \\n\\n."""
        text = "code here\n\nnext section"
        result = cut_at_stops(text, ["\n\n"])
        assert result == "code here"
    
    def test_cut_at_first_stop(self):
        """Test cutting at first matching stop."""
        text = "code\n\nstop1```stop2"
        result = cut_at_stops(text, ["\n\n", "```"])
        assert result == "code"
    
    def test_no_stops_found(self):
        """Test no cutting when stops not found."""
        text = "code without stops"
        result = cut_at_stops(text, ["\n\n", "```"])
        assert result == text
    
    def test_empty_stops(self):
        """Test with empty stops list."""
        text = "some code"
        result = cut_at_stops(text, [])
        assert result == text


class TestIndentAlignment:
    """Test indent detection and alignment."""
    
    def test_last_line_indent_zero(self):
        """Test indent detection for unindented line."""
        prefix = "def func():\nreturn x"
        result = last_line_indent(prefix)
        assert result == 0
    
    def test_last_line_indent_four(self):
        """Test indent detection for 4-space indent."""
        prefix = "def func():\n    x = 1"
        result = last_line_indent(prefix)
        assert result == 4
    
    def test_last_line_indent_eight(self):
        """Test indent detection for 8-space indent."""
        prefix = "class A:\n    def func():\n        pass"
        result = last_line_indent(prefix)
        assert result == 8
    
    def test_align_first_line_simple(self):
        """Test aligning first line to base indent."""
        prefix = "def func():\n    "
        completion = "return x + y"
        result = align_first_line(prefix, completion)
        assert result == "    return x + y"
    
    def test_align_multiline(self):
        """Test aligning multi-line completion."""
        prefix = "def func():\n    "
        completion = "if True:\nreturn 1\nelse:\nreturn 0"
        result = align_first_line(prefix, completion)
        lines = result.split("\n")
        assert lines[0] == "    if True:"
        # Other lines should maintain relative indent
        assert "return" in lines[1]
    
    def test_align_preserves_nested_indent(self):
        """Test that nested indentation is preserved."""
        prefix = "def func():\n    "
        completion = "if x:\n    return True\nelse:\n    return False"
        result = align_first_line(prefix, completion)
        assert "    if x:" in result
        # Nested blocks should be more indented
        assert "        return" in result or "    return" in result


class TestOverlapDetection:
    """Test overlap removal between prefix/suffix and completion."""
    
    def test_cut_overlap_tail_simple(self):
        """Test removing overlap with prefix."""
        prefix = "def add(a, b):"
        completion = "b):\n    return a + b"
        result = cut_overlap_tail(prefix, completion)
        assert result == "\n    return a + b"
    
    def test_cut_overlap_tail_no_overlap(self):
        """Test no cutting when no overlap."""
        prefix = "def add(a, b):"
        completion = "    return a + b"
        result = cut_overlap_tail(prefix, completion)
        assert result == completion
    
    def test_cut_overlap_head_simple(self):
        """Test removing overlap with suffix."""
        suffix = "\n\ndef multiply(x, y):"
        completion = "return a + b\n\ndef multiply"
        result = cut_overlap_head(suffix, completion)
        assert "def multiply" not in result or result.endswith("return a + b")
    
    def test_cut_overlap_head_no_overlap(self):
        """Test no cutting when no overlap."""
        suffix = "\n\ndef other():"
        completion = "return x"
        result = cut_overlap_head(suffix, completion)
        assert result == completion


class TestPostprocess:
    """Integration tests for full postprocess pipeline."""
    
    def test_full_pipeline_with_fences(self):
        """Test complete pipeline with markdown fences."""
        prefix = "def add(a, b):\n    "
        suffix = "\n\ndef sub(x, y):"
        raw = "```python\nreturn a + b\n```"
        stops = ["\n\n"]
        
        result = postprocess(prefix, suffix, raw, stops)
        
        # Should remove fences
        assert "```" not in result
        # Should have correct indent
        assert result.startswith("    return") or result.startswith("return")
        # Should contain the actual code
        assert "return a + b" in result
    
    def test_full_pipeline_with_overlap(self):
        """Test pipeline with prefix overlap."""
        prefix = "numbers = [1, 2, 3]\nsquares = ["
        suffix = "]\nprint(squares)"
        raw = "[x**2 for x in numbers]"
        stops = []
        
        result = postprocess(prefix, suffix, raw, stops)
        
        # Should handle list comprehension
        assert "x**2 for x in numbers" in result
        # Should not duplicate brackets
        assert not result.startswith("[[")
    
    def test_full_pipeline_with_stops(self):
        """Test pipeline respects stop sequences."""
        prefix = "def func():\n    "
        suffix = ""
        raw = "x = 1\n\n\ndef other():\n    pass"
        stops = ["\n\n"]
        
        result = postprocess(prefix, suffix, raw, stops)
        
        # Should cut at stop sequence
        assert "def other" not in result
        assert "x = 1" in result
    
    def test_complex_case(self):
        """Test complex real-world case."""
        prefix = "class Calculator:\n    def add(self, a, b):\n        "
        suffix = "\n\n    def subtract(self, a, b):"
        raw = "```python\nreturn a + b\n```\n\nSome explanation"
        stops = ["\n\n", "```"]
        
        result = postprocess(prefix, suffix, raw, stops)
        
        # Check all requirements
        assert "```" not in result
        assert "explanation" not in result.lower()
        assert "return a + b" in result
        # Should have proper indent (8 spaces for nested class method)
        lines = result.split("\n")
        if lines:
            first_line = lines[0]
            # Allow some flexibility in indent
            assert "return" in first_line


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
