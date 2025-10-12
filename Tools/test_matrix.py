#!/usr/bin/env python3
"""
Test matrix runner for Người 4
Tests various combinations of: Python/JS × sync/stream × token × model
"""

import json
import subprocess
import sys
from typing import Dict, List, Tuple


TEST_CASES = [
    # Format: (name, language, stream, auth, expected_status)
    ("py-sync-auth", "python", False, True, 200),
    ("py-stream-auth", "python", True, True, 200),
    ("py-sync-noauth", "python", False, False, 401),
    ("py-stream-noauth", "python", True, False, 401),
    # Note: JS/TS will fail due to schema validation
    ("js-sync-auth", "javascript", False, True, 422),
    ("ts-stream-auth", "typescript", True, True, 422),
]

SERVER = "http://100.109.118.90:9000"
API_KEY = "5conmeo"


def run_test(name: str, language: str, stream: bool, auth: bool, expected: int) -> Tuple[str, bool, str]:
    """Run single test case, return (name, success, details)"""
    
    cmd = [
        sys.executable, "Tools/cli.py",
        "--server", SERVER,
        "--language", language,
        "--max-tokens", "20",
        "--timeout", "10"
    ]
    
    if auth:
        cmd.extend(["--api-key", API_KEY])
    
    if stream:
        cmd.append("--stream")
    
    test_input = "def test():\n    "
    
    try:
        result = subprocess.run(
            cmd,
            input=test_input,
            text=True,
            capture_output=True,
            timeout=15
        )
        
        # For stream mode, check stderr for HTTP status
        if stream and "HTTP" in result.stderr:
            if f"HTTP {expected}" in result.stderr:
                return name, True, f"Stream got expected HTTP {expected}"
            else:
                return name, False, f"Stream unexpected: {result.stderr.strip()}"
        
        # For sync mode, check return code
        if expected == 200 and result.returncode == 0:
            return name, True, f"Sync success: {result.stdout[:50]}..."
        elif expected != 200 and result.returncode != 0:
            return name, True, f"Sync expected failure: {result.stderr.strip()}"
        else:
            return name, False, f"Unexpected result: rc={result.returncode}, stderr={result.stderr.strip()}"
            
    except subprocess.TimeoutExpired:
        return name, False, "Timeout"
    except Exception as e:
        return name, False, f"Exception: {e}"


def main():
    print("🧪 Running test matrix...")
    print("=" * 50)
    
    results: List[Tuple[str, bool, str]] = []
    
    for name, language, stream, auth, expected in TEST_CASES:
        print(f"Testing {name}...", end=" ")
        result_name, success, details = run_test(name, language, stream, auth, expected)
        results.append((result_name, success, details))
        
        if success:
            print("✅")
        else:
            print("❌")
        print(f"  → {details}")
    
    print("\n" + "=" * 50)
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    print(f"Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()