"""
Integration tests for code completion API with Groq backend.
Tests real API calls to verify end-to-end functionality.
"""
import pytest
import requests
import os
from typing import Dict, Any

# Test server URL (can be overridden with env var)
SERVER_URL = os.getenv("TEST_SERVER_URL", "http://localhost:9000")
API_KEY = os.getenv("TEST_API_KEY", "5conmeo")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


class TestHealthEndpoints:
    """Test health and status endpoints"""
    
    def test_health_check(self):
        """Health endpoint should return OK status"""
        resp = requests.get(f"{SERVER_URL}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ["ok", "degraded"]
        assert "model" in data
        assert "available_models" in data
    
    def test_models_endpoint(self):
        """Models endpoint should list available Groq models"""
        resp = requests.get(f"{SERVER_URL}/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert len(data["data"]) > 0


class TestCompletionEndpoint:
    """Test /complete endpoint with various scenarios"""
    
    def test_basic_completion(self):
        """Basic function completion should work"""
        payload = {
            "prefix": "def add(a, b):\n    ",
            "suffix": "\n\ndef multiply(x, y):",
            "language": "python",
            "max_tokens": 50,
            "temperature": 0.2
        }
        
        resp = requests.post(
            f"{SERVER_URL}/complete",
            headers=HEADERS,
            json=payload
        )
        
        assert resp.status_code == 200
        data = resp.json()
        assert "request_id" in data
        assert "completion" in data
        
        completion = data["completion"]
        # Should return some code
        assert len(completion) > 0
        # Should NOT contain markdown fences
        assert "```" not in completion
        # Should be relevant to function body
        assert "return" in completion.lower() or "=" in completion
    
    def test_completion_no_markdown(self):
        """Completions should never contain markdown fences"""
        payload = {
            "prefix": "def fibonacci(n):\n    if n <= 1:\n        return n\n    ",
            "suffix": "",
            "language": "python",
            "max_tokens": 80,
            "temperature": 0.1
        }
        
        resp = requests.post(
            f"{SERVER_URL}/complete",
            headers=HEADERS,
            json=payload
        )
        
        assert resp.status_code == 200
        completion = resp.json()["completion"]
        
        # Critical: NO markdown
        assert "```" not in completion
        assert not completion.startswith("python")
        assert not completion.startswith("```")
    
    def test_completion_indentation(self):
        """Completion should respect indentation level"""
        payload = {
            "prefix": "class Calculator:\n    def add(self, a, b):\n        ",
            "suffix": "\n\n    def subtract(self, a, b):",
            "language": "python",
            "max_tokens": 40,
            "temperature": 0.2
        }
        
        resp = requests.post(
            f"{SERVER_URL}/complete",
            headers=HEADERS,
            json=payload
        )
        
        assert resp.status_code == 200
        completion = resp.json()["completion"]
        
        # Should not be empty
        assert len(completion) > 0
        # First line should NOT be over-indented
        first_line = completion.split('\n')[0]
        # Should contain return or assignment
        assert "return" in completion or "=" in completion
    
    def test_completion_with_suffix_context(self):
        """Completion should be aware of suffix context"""
        payload = {
            "prefix": "numbers = [1, 2, 3, 4, 5]\nresult = ",
            "suffix": "\nprint(result)",
            "language": "python",
            "max_tokens": 60,
            "temperature": 0.2
        }
        
        resp = requests.post(
            f"{SERVER_URL}/complete",
            headers=HEADERS,
            json=payload
        )
        
        assert resp.status_code == 200
        completion = resp.json()["completion"]
        assert len(completion) > 0
    
    def test_completion_latency(self):
        """Completion should respond within reasonable time"""
        import time
        
        payload = {
            "prefix": "def quicksort(arr):\n    ",
            "suffix": "",
            "language": "python",
            "max_tokens": 100,
            "temperature": 0.2
        }
        
        start = time.time()
        resp = requests.post(
            f"{SERVER_URL}/complete",
            headers=HEADERS,
            json=payload,
            timeout=30
        )
        latency = (time.time() - start) * 1000  # ms
        
        assert resp.status_code == 200
        # Should be reasonably fast (not including Render cold start)
        # Allow up to 10s for warm server
        assert latency < 10000, f"Too slow: {latency}ms"
        
        print(f"✅ Latency: {latency:.0f}ms")


class TestAuthentication:
    """Test API authentication"""
    
    def test_missing_auth_header(self):
        """Request without auth should be rejected"""
        payload = {
            "prefix": "def test():\n    ",
            "suffix": "",
            "language": "python"
        }
        
        resp = requests.post(
            f"{SERVER_URL}/complete",
            json=payload
        )
        
        assert resp.status_code == 403
    
    def test_invalid_api_key(self):
        """Request with wrong API key should be rejected"""
        payload = {
            "prefix": "def test():\n    ",
            "suffix": "",
            "language": "python"
        }
        
        invalid_headers = {
            "Authorization": "Bearer wrong_key",
            "Content-Type": "application/json"
        }
        
        resp = requests.post(
            f"{SERVER_URL}/complete",
            headers=invalid_headers,
            json=payload
        )
        
        assert resp.status_code == 403


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_prefix(self):
        """Should handle empty prefix"""
        payload = {
            "prefix": "",
            "suffix": "print('hello')",
            "language": "python",
            "max_tokens": 50
        }
        
        resp = requests.post(
            f"{SERVER_URL}/complete",
            headers=HEADERS,
            json=payload
        )
        
        # Should not error, but might return minimal completion
        assert resp.status_code == 200
    
    def test_large_context(self):
        """Should handle large prefix context"""
        large_prefix = "def complex_function(data):\n    " + "# comment\n    " * 50
        
        payload = {
            "prefix": large_prefix,
            "suffix": "",
            "language": "python",
            "max_tokens": 100
        }
        
        resp = requests.post(
            f"{SERVER_URL}/complete",
            headers=HEADERS,
            json=payload
        )
        
        assert resp.status_code == 200
    
    def test_max_tokens_limit(self):
        """Should respect max_tokens parameter"""
        payload = {
            "prefix": "def count_to_hundred():\n    ",
            "suffix": "",
            "language": "python",
            "max_tokens": 10  # Very small limit
        }
        
        resp = requests.post(
            f"{SERVER_URL}/complete",
            headers=HEADERS,
            json=payload
        )
        
        assert resp.status_code == 200
        completion = resp.json()["completion"]
        # Should be short due to token limit
        assert len(completion) < 200


if __name__ == "__main__":
    # Run with: pytest server/tests/test_integration.py -v
    # Or: python server/tests/test_integration.py
    pytest.main([__file__, "-v", "--tb=short"])
