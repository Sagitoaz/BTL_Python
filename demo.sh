#!/bin/bash
# Demo script cho Người 4
# Chạy: chmod +x demo.sh && ./demo.sh

set -e

echo "🚀 Demo BTL AI Code Completion"
echo "================================"

# 1. Kiểm tra server health
echo -e "\n1️⃣ Checking server health..."
curl -s http://100.109.118.90:9000/health | jq .

# 2. Demo CLI sync
echo -e "\n2️⃣ CLI Sync completion..."
echo "def add(a, b):" | python Tools/cli.py --server http://100.109.118.90:9000 --api-key 5conmeo --strip-fence

# 3. Demo CLI stream  
echo -e "\n3️⃣ CLI Stream completion..."
echo "def factorial(n):" | python Tools/cli.py --server http://100.109.118.90:9000 --api-key 5conmeo --stream --strip-fence

# 4. Quick stress test
echo -e "\n4️⃣ Quick stress test (10 requests)..."
python Tools/stress.py --server http://100.109.118.90:9000 --api-key 5conmeo --requests 10 --concurrency 3 --timeout 10

echo -e "\n✅ Demo completed!"