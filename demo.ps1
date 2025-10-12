# Demo script cho Người 4 - Windows PowerShell
# Chạy: Set-ExecutionPolicy -Scope Process Bypass; .\demo.ps1

Write-Host "🚀 Demo BTL AI Code Completion" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Yellow

# 1. Kiểm tra server health
Write-Host "`n1️⃣ Checking server health..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod "http://100.109.118.90:9000/health"
    $health | ConvertTo-Json -Depth 2
} catch {
    Write-Host "❌ Server health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 2. Demo CLI sync
Write-Host "`n2️⃣ CLI Sync completion..." -ForegroundColor Cyan
$prefix = "def add(a, b):"
$prefix | C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/cli.py --server http://100.109.118.90:9000 --api-key 5conmeo --strip-fence

# 3. Demo CLI stream  
Write-Host "`n3️⃣ CLI Stream completion..." -ForegroundColor Cyan
$prefix2 = "def factorial(n):"
$prefix2 | C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/cli.py --server http://100.109.118.90:9000 --api-key 5conmeo --stream --strip-fence

# 4. Quick stress test
Write-Host "`n4️⃣ Quick stress test (10 requests)..." -ForegroundColor Cyan
C:/BTL_python/BTL_Python/.venv/Scripts/python.exe Tools/stress.py --server http://100.109.118.90:9000 --api-key 5conmeo --requests 10 --concurrency 3 --timeout 10

Write-Host "`n✅ Demo completed!" -ForegroundColor Green