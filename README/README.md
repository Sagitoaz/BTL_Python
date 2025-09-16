Ngày 1 – CLI Tester (tools/cli.py)
Mục đích

Gửi prefix code đến API /complete và nhận completion.

Hỗ trợ chế độ stream qua /complete_stream (SSE).

.\.venv\Scripts\Activate.ps1
môi trường ảo

Cách chạy

# Linux/Mac

echo "def add(a, b):\n " | python tools/cli.py --server http://SERVER:9000 --api-key TOKEN

# Windows PowerShell (dùng `n` thay vì \n)

$prefix = "def add(a, b):`n    "
$prefix | python tools/cli.py --server http://SERVER:9000 --api-key TOKEN

Tham số chính

--server: URL server (VD: http://100.109.118.90:9000)

--api-key: API key (VD: 5conmeo)

--stream: Bật stream, in từng delta

--max-tokens: số token tối đa model sinh ra

--strip-fence: bỏ code fence ``` khi in kết quả

Ngày 2 – Stress Tester (tools/stress.py)
Mục đích

Gửi nhiều request song song đến /complete.

Đo QPS, p95, p99 latency.

Log lỗi, phân loại CONNECTION/TIMEOUT/HTTP_xxx.

Cách chạy

# 200 request, 20 request song song, timeout 8s

python tools/stress.py --server http://SERVER:9000 --api-key TOKEN --requests 200 --concurrency 20 --timeout 8

Dùng payload tùy chỉnh

Tạo file payload.json:

{
"prefix": "def factorial(n):\n ",
"suffix": "\n",
"language": "python",
"max_tokens": 64,
"temperature": 0.2
}

Chạy:

python tools/stress.py --server http://SERVER:9000 --api-key TOKEN --requests 100 --concurrency 10 --payload-file payload.json

Ngày 3 – Script đa nền tảng
Mục đích

Cho cả nhóm test nhanh server (không cần biết Python).

Kiểm tra 4 endpoint chính: /health, /models, /complete, /complete_stream.

Linux/Mac (scripts/quick-test.sh)
chmod +x scripts/quick-test.sh
./scripts/quick-test.sh

Windows (scripts/quick-test.ps1)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\quick-test.ps1

Kết quả kỳ vọng

/health → { "status": "ok", ... }

/models → Danh sách model

/complete → JSON chứa completion

/complete_stream → Chuỗi delta in dần theo thời gian thực

👉 Các file này không thay thế nhau:

cli.py → dành cho dev test chi tiết, có nhiều option.

stress.py → benchmark hiệu năng.

quick-test.sh / quick-test.ps1 → test nhanh cho cả nhóm, demo trực quan.
