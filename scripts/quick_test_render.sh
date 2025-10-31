#!/bin/bash
# Quick test cho server Render
# Usage: ./quick_test_render.sh

SERVER_URL="https://btl-python-r9kz.onrender.com"
API_KEY="5conmeo"

echo "🧪 Testing Render Server"
echo "URL: $SERVER_URL"
echo ""

# Test 1: Health
echo "📋 Test 1: Health Check"
HEALTH=$(curl -s "$SERVER_URL/health")
echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"

STATUS=$(echo "$HEALTH" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
if [ "$STATUS" = "ok" ]; then
    echo "✅ Server OK - Ollama connected"
elif [ "$STATUS" = "degraded" ]; then
    echo "⚠️  Server chạy nhưng chưa connect Ollama"
    echo ""
    echo "Cần set OLLAMA_URL trong Render Environment:"
    echo "1. Chạy ngrok: ./scripts/expose_ollama_ngrok.sh"
    echo "2. Copy URL ngrok"
    echo "3. Set trong Render Dashboard → Environment → OLLAMA_URL"
    exit 1
else
    echo "❌ Server có vấn đề"
    exit 1
fi
echo ""

# Test 2: Completion
echo "📋 Test 2: Code Completion"
COMPLETION=$(curl -s -X POST "$SERVER_URL/complete" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "prefix": "def add(a, b):\n    ",
    "suffix": "\n",
    "language": "python",
    "max_tokens": 50,
    "temperature": 0.2
  }')

echo "$COMPLETION" | python3 -m json.tool 2>/dev/null || echo "$COMPLETION"

# Check for markdown
if echo "$COMPLETION" | grep -q '```'; then
    echo "⚠️  WARNING: Output có markdown fences"
else
    echo "✅ Postprocessing OK - Không có markdown"
fi
echo ""

echo "================================"
echo "✅ Tests completed!"
echo ""
echo "Next steps:"
echo "1. Open VSCode"
echo "2. Open a Python file"
echo "3. Start typing to test completions"
echo "4. Extension settings đã update trong .vscode/settings.json"
