#!/bin/bash
# Script test server sau khi deploy lên Render
# Usage: ./test_render_server.sh <server-url>

if [ -z "$1" ]; then
    echo "❌ Thiếu server URL!"
    echo ""
    echo "Usage: $0 <server-url>"
    echo "Example: $0 https://btl-python-server.onrender.com"
    exit 1
fi

SERVER_URL="$1"
API_KEY="5conmeo"

echo "🧪 Testing server at: $SERVER_URL"
echo ""

# Test 1: Health check
echo "📋 Test 1: Health Check"
echo "GET $SERVER_URL/health"
HEALTH_RESPONSE=$(curl -s "$SERVER_URL/health")
echo "Response: $HEALTH_RESPONSE"

if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
    echo "✅ Health check PASSED"
else
    echo "❌ Health check FAILED"
    exit 1
fi
echo ""

# Test 2: Completion endpoint
echo "📋 Test 2: Code Completion"
echo "POST $SERVER_URL/v1/completions"

COMPLETION_RESPONSE=$(curl -s -X POST "$SERVER_URL/v1/completions" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "prefix": "def add(a, b):\n    ",
    "suffix": "\n\nprint(add(1, 2))",
    "language": "python",
    "max_tokens": 50,
    "temperature": 0.2
  }')

echo "Response:"
echo "$COMPLETION_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$COMPLETION_RESPONSE"

if echo "$COMPLETION_RESPONSE" | grep -q 'choices\|completion'; then
    echo "✅ Completion test PASSED"
else
    echo "❌ Completion test FAILED"
    echo ""
    echo "Possible issues:"
    echo "- OLLAMA_URL not set correctly"
    echo "- Ollama server not reachable from Render"
    echo "- API_KEY incorrect"
    exit 1
fi
echo ""

# Test 3: Postprocessing (no markdown)
echo "📋 Test 3: Postprocessing Check"
if echo "$COMPLETION_RESPONSE" | grep -q '```'; then
    echo "⚠️  WARNING: Response contains markdown fences (```)"
    echo "Check POSTPROCESS_ENABLED=true in Render env vars"
else
    echo "✅ Postprocessing working - no markdown fences found"
fi
echo ""

echo "================================"
echo "✅ ALL TESTS COMPLETED!"
echo "================================"
echo ""
echo "Server URL: $SERVER_URL"
echo "Status: Ready to use"
echo ""
echo "Next steps:"
echo "1. Update VSCode extension with this URL"
echo "2. Test extension in VSCode"
echo "3. Monitor logs in Render Dashboard"
