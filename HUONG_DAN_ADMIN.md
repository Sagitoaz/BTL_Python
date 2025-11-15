# HƯỚNG DẪN ADMIN - XEM TELEMETRY VÀ USER PROFILES

## 1. XEM THỐNG KÊ TELEMETRY

### Cách 1: Sử dụng curl (command line)

```bash
# Xem thống kê tổng quan
curl -X GET "https://btl-python-r9kz.onrender.com/admin/telemetry/stats" \
  -H "Authorization: Bearer 5conmeo"
```

**Response mẫu:**
```json
{
  "total_completions": 1245,
  "languages": {
    "python": 834,
    "cpp": 411
  },
  "avg_latency_ms": 687.3,
  "data_files": 3
}
```

### Cách 2: Sử dụng Postman/Insomnia

1. Tạo request mới:
   - **Method:** GET
   - **URL:** `https://btl-python-r9kz.onrender.com/admin/telemetry/stats`
   - **Headers:**
     - `Authorization`: `Bearer 5conmeo`

2. Click "Send" để xem kết quả

### Cách 3: Format JSON đẹp hơn với jq

```bash
curl -X GET "https://btl-python-r9kz.onrender.com/admin/telemetry/stats" \
  -H "Authorization: Bearer 5conmeo" | jq .
```

---

## 2. XEM CHI TIẾT TELEMETRY DATA

### Các file telemetry được lưu ở đâu?

Trên server, data được lưu tại: `server/data/telemetry/telemetry_YYYYMMDD.jsonl`

**Ví dụ:**
- `telemetry_20251111.jsonl` - Data của ngày 11/11/2025
- `telemetry_20251110.jsonl` - Data của ngày 10/11/2025

### Cấu trúc 1 record telemetry:

```json
{
  "timestamp": "2025-11-11T14:23:45.123456",
  "request_id": "req_abc123xyz",
  "user_id": "a1b2c3d4e5f6g7h8",
  "language": "python",
  "prefix": "def calculate_sum(numbers):\n    ",
  "suffix": "\n\nresult = calculate_sum([1, 2, 3])",
  "completion": "if not numbers:\n        return 0\n    return sum(numbers)",
  "latency_ms": 687.3,
  "model": "llama-3.3-70b-versatile",
  "accepted": true,
  "prefix_length": 35,
  "suffix_length": 42,
  "completion_length": 68,
  "completion_lines": 3
}
```

### Xem trực tiếp trên server:

```bash
# SSH vào server (nếu có quyền)
ssh user@server

# Xem 10 records mới nhất
tail -10 server/data/telemetry/telemetry_20251111.jsonl

# Đếm số requests hôm nay
wc -l server/data/telemetry/telemetry_20251111.jsonl

# Filter theo ngôn ngữ Python
grep '"language": "python"' server/data/telemetry/telemetry_20251111.jsonl | wc -l
```

---

## 3. EXPORT DATA ĐỂ PHÂN TÍCH

### Export sang JSONL (để train model)

```bash
curl -X POST "https://btl-python-r9kz.onrender.com/admin/telemetry/export?format=jsonl" \
  -H "Authorization: Bearer 5conmeo"
```

**Response:**
```json
{
  "status": "success",
  "records_exported": 1245,
  "file": "data/exports/training_data.jsonl"
}
```

### Download file đã export

```bash
curl -X GET "https://btl-python-r9kz.onrender.com/admin/telemetry/download/training_data.jsonl" \
  -H "Authorization: Bearer 5conmeo" \
  -o training_data.jsonl
```

### Export sang CSV (để phân tích Excel/Pandas)

```bash
curl -X POST "https://btl-python-r9kz.onrender.com/admin/telemetry/export?format=csv" \
  -H "Authorization: Bearer 5conmeo"
```

---

## 4. XEM TELEMETRY FILES TRỰC TIẾP TRÊN SERVER

### Nếu có quyền SSH vào Render:

```bash
# Xem 10 records mới nhất
tail -10 data/telemetry/telemetry_$(date +%Y%m%d).jsonl

# Đếm số requests hôm nay
wc -l data/telemetry/telemetry_$(date +%Y%m%d).jsonl

# Filter theo Python
grep '"language": "python"' data/telemetry/*.jsonl | wc -l

# Xem requests 1 giờ gần nhất
grep $(date -d '1 hour ago' '+%Y-%m-%dT%H') data/telemetry/*.jsonl

# Tính average latency
grep -o '"latency_ms": [0-9.]*' data/telemetry/*.jsonl | \
  awk -F': ' '{sum+=$2; count++} END {print sum/count "ms"}'
```

---

## 5. PHÂN TÍCH DATA VỚI JQ VÀ AWK

### Đếm requests theo ngôn ngữ:

```bash
# Đếm Python requests
cat data/telemetry/*.jsonl | grep '"language": "python"' | wc -l

# Đếm C++ requests  
cat data/telemetry/*.jsonl | grep '"language": "cpp"' | wc -l

# Top 10 users có nhiều requests nhất
cat data/telemetry/*.jsonl | jq -r '.user_id' | sort | uniq -c | sort -rn | head -10

# Tính accept rate
total=$(cat data/telemetry/*.jsonl | wc -l)
accepted=$(cat data/telemetry/*.jsonl | jq -r '.accepted' | grep -c true)
echo "Accept rate: $(echo "scale=2; $accepted * 100 / $total" | bc)%"
```

### Phân tích latency:

```bash
# Latency trung bình
cat data/telemetry/*.jsonl | jq -r '.latency_ms' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count "ms"}'

# Latency min/max
cat data/telemetry/*.jsonl | jq -r '.latency_ms' | sort -n | \
  awk 'NR==1 {min=$1} END {print "Min:", min "ms\nMax:", $1 "ms"}'

# Requests chậm hơn 2 giây
cat data/telemetry/*.jsonl | jq 'select(.latency_ms > 2000)'
```

### Export sang CSV:

```bash
# Convert JSONL to CSV
cat data/telemetry/*.jsonl | jq -r '
  [.timestamp, .user_id, .language, .latency_ms, .completion_length, .accepted] 
  | @csv
' > telemetry.csv

# Thêm header
echo "timestamp,user_id,language,latency_ms,completion_length,accepted" | \
  cat - telemetry.csv > telemetry_with_header.csv
```

---

## 6. MONITOR REAL-TIME VỚI WATCH

```bash
# Refresh stats mỗi 5 giây
watch -n 5 'curl -s -H "Authorization: Bearer 5conmeo" \
  https://btl-python-r9kz.onrender.com/admin/telemetry/stats | jq .'

# Xem file telemetry real-time (trên server)
tail -f data/telemetry/telemetry_$(date +%Y%m%d).jsonl | jq .

# Count requests theo thời gian thực
watch -n 1 'wc -l data/telemetry/telemetry_$(date +%Y%m%d).jsonl'
```

---

## 7. TÓM TẮT COMMANDS

```bash
# 1. Xem stats tổng quan
curl -H "Authorization: Bearer 5conmeo" \
  https://btl-python-r9kz.onrender.com/admin/telemetry/stats | jq .

# 2. Export data
curl -X POST -H "Authorization: Bearer 5conmeo" \
  "https://btl-python-r9kz.onrender.com/admin/telemetry/export?format=jsonl"

# 3. Download file
curl -H "Authorization: Bearer 5conmeo" \
  https://btl-python-r9kz.onrender.com/admin/telemetry/download/training_data.jsonl \
  -o training_data.jsonl

# 4. Đếm theo ngôn ngữ (local)
cat data/telemetry/*.jsonl | jq -r '.language' | sort | uniq -c

# 5. Tính latency trung bình (local)
cat data/telemetry/*.jsonl | jq -r '.latency_ms' | \
  awk '{sum+=$1; n++} END {print sum/n "ms"}'

# 6. Top 10 active users (local)
cat data/telemetry/*.jsonl | jq -r '.user_id' | sort | uniq -c | sort -rn | head -10
```

---

## 8. XEM USER PROFILING

### 8.1. Liệt kê tất cả user profiles

```bash
curl -X GET "https://btl-python-r9kz.onrender.com/admin/profiles/list" \
  -H "Authorization: Bearer 5conmeo"
```

**Response mẫu:**
```json
{
  "total_users": 3,
  "profiles": [
    {
      "user_id": "test-user-123",
      "total_samples": 15,
      "accept_rate": 0.75,
      "last_updated": "2025-11-13T10:30:00"
    },
    {
      "user_id": "abc123def456",
      "total_samples": 8,
      "accept_rate": 0.625,
      "last_updated": "2025-11-13T09:15:00"
    }
  ]
}
```

### 8.2. Xem chi tiết profile của 1 user

```bash
curl -X GET "https://btl-python-r9kz.onrender.com/admin/profiles/test-user-123" \
  -H "Authorization: Bearer 5conmeo" | python3 -m json.tool
```

**Response mẫu:**
```json
{
  "user_id": "test-user-123",
  "coding_style": {
    "indent_size": 4,
    "uses_tabs": false,
    "prefers_single_quotes": false,
    "prefers_snake_case": true,
    "avg_line_length": 78,
    "max_line_length": 120,
    "uses_type_hints": false,
    "uses_docstrings": false,
    "comment_frequency": 0.1,
    "total_samples": 15,
    "last_updated": "2025-11-13T10:30:00"
  },
  "accept_rate": 0.75,
  "avg_accept_time_ms": 1200.5,
  "preferred_completion_length": 50,
  "prefers_multi_line": true,
  "common_libraries": ["pandas", "numpy"],
  "created_at": "2025-11-12T14:00:00",
  "updated_at": "2025-11-13T10:30:00"
}
```

### 8.3. Xem style hints cho user

Style hints là các gợi ý về phong cách code được gửi tới LLM để cá nhân hóa completions.

```bash
curl -X GET "https://btl-python-r9kz.onrender.com/admin/profiles/test-user-123/style-hints" \
  -H "Authorization: Bearer 5conmeo"
```

**Response mẫu:**
```json
{
  "user_id": "test-user-123",
  "style_hints": "User's coding style: Use 4 spaces for indentation; Prefer double quotes for strings; Use snake_case naming; Keep lines under 120 characters; Include type hints."
}
```

### 8.4. Cách hoạt động của User Profiling

**Quy trình:**

1. **User dùng extension** → Tạo completion với header `X-User-ID`
2. **User accept/reject** suggestion trong VS Code
3. **Extension gửi feedback** tới `/feedback/completion`:
   ```bash
   curl -X POST "https://btl-python-r9kz.onrender.com/feedback/completion" \
     -H "Authorization: Bearer 5conmeo" \
     -H "Content-Type: application/json" \
     -H "X-User-ID: test-user-123" \
     -d '{
       "request_id": "abc123",
       "accepted": true,
       "completion_text": "return a + b",
       "prefix": "def add(a, b):\n    ",
       "accept_time_ms": 1200.5
     }'
   ```

4. **Server phân tích code** → Update profile:
   - Indent size (tabs/spaces, số lượng)
   - Quote preference (single/double quotes)
   - Naming convention (snake_case/camelCase)
   - Line length trung bình
   - Type hints usage
   - Docstrings usage
   - Comment frequency

5. **Lần sau user request** → Server gửi style hints tới LLM → Completion phù hợp hơn

### 8.5. Phân tích data từ profiles

**Đếm users theo accept rate:**
```bash
curl -s -H "Authorization: Bearer 5conmeo" \
  https://btl-python-r9kz.onrender.com/admin/profiles/list | \
  jq '.profiles[] | select(.accept_rate >= 0.7) | .user_id'
```

**Tìm users active nhất (nhiều samples):**
```bash
curl -s -H "Authorization: Bearer 5conmeo" \
  https://btl-python-r9kz.onrender.com/admin/profiles/list | \
  jq '.profiles | sort_by(.total_samples) | reverse | .[0:5]'
```

**Lấy danh sách user IDs:**
```bash
curl -s -H "Authorization: Bearer 5conmeo" \
  https://btl-python-r9kz.onrender.com/admin/profiles/list | \
  jq -r '.profiles[].user_id'
```

### 8.6. File lưu trữ User Profiles

Profiles được lưu tại: `server/data/user_profiles/{user_id}.json`

**⚠️ Lưu ý:** Giống telemetry, data profiles cũng **mất khi server restart** trên Render free tier vì không có persistent storage!

---

## 9. BẢO MẬT

⚠️ **QUAN TRỌNG:**

1. **Đổi API key mặc định** (`5conmeo`) trong production
2. **Whitelist IP** cho admin endpoints nếu có thể
3. **Enable HTTPS** (Render tự động có sẵn)
4. **Không log sensitive data** (passwords, personal info)
5. **Rotate API keys** định kỳ (3-6 tháng)

---

**✅ Bây giờ bạn đã có thể monitor và phân tích toàn bộ hệ thống!**
