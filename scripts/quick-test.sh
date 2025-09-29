mkdir -p scripts
cat > scripts/quick-test.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
SERVER="${SERVER:-http://100.109.118.90:9000}"
TOKEN="${API_KEY:-5conmeo}"

echo "== /health =="
curl -s "$SERVER/health" | jq .

echo "== /models =="
curl -s -H "Authorization: Bearer $TOKEN" "$SERVER/models" | jq .

echo "== /complete (sync) =="
curl -s -X POST "$SERVER/complete" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prefix":"def two_sum(nums, target):\n    ","suffix":"\n","language":"python","max_tokens":64,"temperature":0.2}' | jq .

echo "== /complete_stream (SSE) =="
curl -s -N -X POST "$SERVER/complete_stream" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prefix":"def two_sum(nums, target):\n    ","suffix":"\n","language":"python","max_tokens":64,"temperature":0.2}'
echo
EOF
chmod +x scripts/quick-test.sh
