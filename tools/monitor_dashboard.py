"""
Real-time monitoring dashboard for code completion service.
Tracks metrics: accuracy, latency, usage, errors.
"""
import time
import requests
import statistics
from datetime import datetime
from typing import List, Dict
import json


class CompletionMonitor:
    """Monitor and track completion API metrics"""
    
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.metrics = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "latencies": [],
            "errors": [],
            "completion_lengths": [],
            "markdown_detections": 0
        }
    
    def check_health(self) -> Dict:
        """Check server health"""
        try:
            resp = requests.get(f"{self.server_url}/health", timeout=5)
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def test_completion(self, prefix: str, suffix: str = "", language: str = "python") -> Dict:
        """Test a single completion and record metrics"""
        self.metrics["total_requests"] += 1
        
        payload = {
            "prefix": prefix,
            "suffix": suffix,
            "language": language,
            "max_tokens": 100,
            "temperature": 0.2
        }
        
        start_time = time.time()
        
        try:
            resp = requests.post(
                f"{self.server_url}/complete",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            latency = (time.time() - start_time) * 1000  # ms
            self.metrics["latencies"].append(latency)
            
            if resp.status_code == 200:
                self.metrics["successful"] += 1
                data = resp.json()
                completion = data.get("completion", "")
                
                # Track metrics
                self.metrics["completion_lengths"].append(len(completion))
                
                # Check for markdown
                if "```" in completion:
                    self.metrics["markdown_detections"] += 1
                
                return {
                    "status": "success",
                    "latency_ms": latency,
                    "completion": completion,
                    "has_markdown": "```" in completion,
                    "length": len(completion)
                }
            else:
                self.metrics["failed"] += 1
                error = resp.text[:200]
                self.metrics["errors"].append(error)
                return {
                    "status": "error",
                    "error": error,
                    "status_code": resp.status_code
                }
                
        except Exception as e:
            self.metrics["failed"] += 1
            error = str(e)
            self.metrics["errors"].append(error)
            return {"status": "exception", "error": error}
    
    def run_test_suite(self, test_cases: List[Dict]) -> Dict:
        """Run a suite of test completions"""
        print(f"\n{'='*60}")
        print(f"🧪 RUNNING TEST SUITE: {len(test_cases)} cases")
        print(f"{'='*60}\n")
        
        results = []
        
        for i, test in enumerate(test_cases, 1):
            print(f"Test {i}/{len(test_cases)}: {test.get('name', 'Unnamed')}")
            
            result = self.test_completion(
                prefix=test["prefix"],
                suffix=test.get("suffix", ""),
                language=test.get("language", "python")
            )
            
            result["test_name"] = test.get("name", f"Test {i}")
            results.append(result)
            
            # Print result
            if result["status"] == "success":
                latency = result["latency_ms"]
                has_md = "❌ MARKDOWN" if result["has_markdown"] else "✅"
                print(f"  ✅ {latency:.0f}ms | {has_md} | {result['length']} chars")
            else:
                print(f"  ❌ FAILED: {result.get('error', 'Unknown')[:50]}")
            
            time.sleep(0.5)  # Rate limiting
        
        return results
    
    def print_summary(self):
        """Print monitoring summary"""
        print(f"\n{'='*60}")
        print(f"📊 MONITORING SUMMARY")
        print(f"{'='*60}\n")
        
        total = self.metrics["total_requests"]
        success = self.metrics["successful"]
        failed = self.metrics["failed"]
        
        print(f"Total Requests: {total}")
        print(f"✅ Successful: {success} ({success/total*100:.1f}%)" if total > 0 else "✅ Successful: 0")
        print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)" if total > 0 else "❌ Failed: 0")
        
        if self.metrics["latencies"]:
            latencies = self.metrics["latencies"]
            print(f"\n⏱️  LATENCY STATS:")
            print(f"  Min: {min(latencies):.0f}ms")
            print(f"  Max: {max(latencies):.0f}ms")
            print(f"  Avg: {statistics.mean(latencies):.0f}ms")
            print(f"  P50: {statistics.median(latencies):.0f}ms")
            if len(latencies) >= 10:
                p95 = sorted(latencies)[int(len(latencies) * 0.95)]
                print(f"  P95: {p95:.0f}ms")
        
        if self.metrics["completion_lengths"]:
            lengths = self.metrics["completion_lengths"]
            print(f"\n📏 COMPLETION LENGTH:")
            print(f"  Min: {min(lengths)} chars")
            print(f"  Max: {max(lengths)} chars")
            print(f"  Avg: {statistics.mean(lengths):.0f} chars")
        
        if self.metrics["markdown_detections"] > 0:
            md_rate = self.metrics["markdown_detections"] / success * 100 if success > 0 else 0
            print(f"\n🔴 MARKDOWN DETECTIONS: {self.metrics['markdown_detections']} ({md_rate:.1f}%)")
        else:
            print(f"\n✅ NO MARKDOWN DETECTED")
        
        if self.metrics["errors"]:
            print(f"\n❌ RECENT ERRORS:")
            for error in self.metrics["errors"][-3:]:
                print(f"  - {error[:100]}")
        
        print(f"\n{'='*60}\n")


def get_standard_test_cases() -> List[Dict]:
    """Standard test cases for monitoring"""
    return [
        {
            "name": "Simple function",
            "prefix": "def add(a, b):\n    ",
            "suffix": "\n\ndef multiply(x, y):"
        },
        {
            "name": "Fibonacci",
            "prefix": "def fibonacci(n):\n    if n <= 1:\n        return n\n    ",
            "suffix": ""
        },
        {
            "name": "Class method",
            "prefix": "class Calculator:\n    def divide(self, a, b):\n        ",
            "suffix": "\n\n    def power(self, x, y):"
        },
        {
            "name": "List comprehension",
            "prefix": "numbers = [1, 2, 3, 4, 5]\nsquares = [",
            "suffix": "]\nprint(squares)"
        },
        {
            "name": "Try-except block",
            "prefix": "try:\n    result = 10 / 0\nexcept ",
            "suffix": "\n    print('Error occurred')"
        },
        {
            "name": "For loop with context",
            "prefix": "users = ['Alice', 'Bob', 'Charlie']\nfor user in users:\n    ",
            "suffix": "\nprint('Done')"
        },
        {
            "name": "Dictionary comprehension",
            "prefix": "names = ['a', 'b', 'c']\nname_dict = {",
            "suffix": "}\nprint(name_dict)"
        },
        {
            "name": "Nested function",
            "prefix": "def outer(x):\n    def inner(y):\n        ",
            "suffix": "\n    return inner\n\nresult = outer(5)"
        }
    ]


def main():
    """Main monitoring function"""
    import sys
    
    # Configuration
    server_url = sys.argv[1] if len(sys.argv) > 1 else "https://btl-python-r9kz.onrender.com"
    api_key = sys.argv[2] if len(sys.argv) > 2 else "5conmeo"
    
    monitor = CompletionMonitor(server_url, api_key)
    
    # Check health first
    print(f"\n🏥 Checking server health...")
    health = monitor.check_health()
    print(f"Status: {health.get('status')}")
    print(f"Model: {health.get('model', 'N/A')}")
    print(f"Available models: {len(health.get('available_models', []))}")
    
    if health.get("status") != "ok":
        print(f"\n⚠️  Server status is not OK. Continue anyway? (y/n)")
        if input().lower() != 'y':
            return
    
    # Run test suite
    test_cases = get_standard_test_cases()
    results = monitor.run_test_suite(test_cases)
    
    # Print summary
    monitor.print_summary()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"tools/monitor_results_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "server_url": server_url,
            "health": health,
            "metrics": monitor.metrics,
            "results": results
        }, f, indent=2)
    
    print(f"📝 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
