# Giải thích chi tiết: `server/app/routers/admin.py`

## 📋 Mục đích của file

File này implement **Admin Endpoints** để:
1. **Xem thống kê telemetry** (GET `/admin/telemetry/stats`)
2. **Export training data** (POST `/admin/telemetry/export`)
3. **Download exported files** (GET `/admin/telemetry/download/{filename}`)
4. **Quản lý dữ liệu** cho model training và analysis

---

## 🔍 Phân tích từng phần

### Import statements

```python
"""
Admin endpoints for telemetry management.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import os

from app.core.security import require_api_key
from app.middleware.telemetry import get_telemetry_collector
```

**Giải thích:**

- `APIRouter`: Route grouping
- `Depends`: Dependency injection (authentication)
- `HTTPException`: HTTP errors
- `FileResponse`: Return files for download
- `os`: File system operations (mkdir, exists)
- `require_api_key`: Authentication dependency
- `get_telemetry_collector`: Singleton telemetry instance

---

## 🛠️ Router Setup

```python
router = APIRouter(prefix="/admin", tags=["admin"])
```

**Configuration:**

#### `prefix="/admin"`
- All endpoints start with `/admin`
- URLs: `/admin/telemetry/stats`, `/admin/telemetry/export`, etc.
- Clear separation from public endpoints

#### `tags=["admin"]`
- OpenAPI/Swagger grouping
- Docs UI: Separate section for admin endpoints

**Security note:**
- All endpoints require authentication
- Use `dependencies=[Depends(require_api_key)]`

---

## 📊 Endpoint: GET `/admin/telemetry/stats`

### Purpose
**Xem thống kê tổng quan** về telemetry data

### Code

```python
@router.get("/telemetry/stats", dependencies=[Depends(require_api_key)])
def get_telemetry_stats():
    """Get telemetry statistics"""
    collector = get_telemetry_collector()
    return collector.get_stats()
```

---

### Phân tích chi tiết

#### Route Declaration

```python
@router.get("/telemetry/stats", dependencies=[Depends(require_api_key)])
```

**Full path:** `/admin/telemetry/stats`

**Authentication required:**
```http
GET /admin/telemetry/stats
Authorization: Bearer sk_abc123...
```

**Without auth:**
```http
GET /admin/telemetry/stats
→ 401 Unauthorized
```

---

#### Get Statistics

```python
    collector = get_telemetry_collector()
    return collector.get_stats()
```

**Flow:**
1. Get singleton telemetry collector
2. Call `get_stats()` method
3. Return statistics dict

**See:** `app.middleware.telemetry.get_stats()` (explained in 02_telemetry.py.md)

---

### Response Example

```json
{
  "total_requests": 1500,
  "successful_requests": 1425,
  "failed_requests": 75,
  "languages": {
    "python": 800,
    "typescript": 500,
    "javascript": 150,
    "cpp": 50
  },
  "models": {
    "groq/deepseek-coder-6.7b-instruct": 1000,
    "groq/llama3-70b": 500
  },
  "avg_latency_ms": 245.67,
  "total_completion_len": 154200
}
```

---

### Use Cases

**1. Monitoring Dashboard:**
```typescript
// Admin dashboard
async function loadStats() {
    const response = await fetch('/admin/telemetry/stats', {
        headers: {'Authorization': 'Bearer admin-key'}
    });
    const stats = await response.json();
    
    // Display metrics
    document.getElementById('total').innerText = stats.total_requests;
    document.getElementById('success-rate').innerText = 
        `${(stats.successful_requests / stats.total_requests * 100).toFixed(1)}%`;
    document.getElementById('avg-latency').innerText = 
        `${stats.avg_latency_ms.toFixed(0)}ms`;
}
```

**2. Alerting:**
```python
# Check if error rate too high
stats = requests.get('/admin/telemetry/stats', headers={...}).json()
error_rate = stats['failed_requests'] / stats['total_requests']

if error_rate > 0.1:  # 10% error threshold
    send_alert(f"⚠️ High error rate: {error_rate*100:.1f}%")
```

**3. Capacity Planning:**
```python
# Analyze language distribution
stats = get_stats()
for lang, count in stats['languages'].items():
    percentage = count / stats['total_requests'] * 100
    print(f"{lang}: {percentage:.1f}%")

# Output:
# python: 53.3%
# typescript: 33.3%
# javascript: 10.0%
# cpp: 3.3%

# Decision: Focus Python optimizations (majority usage)
```

---

## 💾 Endpoint: POST `/admin/telemetry/export`

### Purpose
**Export telemetry data** cho model training hoặc analysis

### Code

```python
@router.post("/telemetry/export", dependencies=[Depends(require_api_key)])
def export_telemetry(format: str = "jsonl"):
    """
    Export telemetry data for training.
    
    Args:
        format: Export format ("jsonl" or "csv")
    """
    if format not in ("jsonl", "csv"):
        raise HTTPException(status_code=400, detail="Format must be 'jsonl' or 'csv'")
    
    collector = get_telemetry_collector()
    output_file = f"data/exports/training_data.{format}"
    
    # Create exports directory
    os.makedirs("data/exports", exist_ok=True)
    
    count = collector.export_training_data(output_file, format=format)
    
    return {
        "status": "success",
        "records_exported": count,
        "file": output_file
    }
```

---

### Phân tích chi tiết

#### Query Parameter

```python
def export_telemetry(format: str = "jsonl"):
```

**Usage:**
```http
POST /admin/telemetry/export?format=jsonl
POST /admin/telemetry/export?format=csv
POST /admin/telemetry/export  (default: jsonl)
```

**Default value:** `"jsonl"`

---

#### Validate Format

```python
    if format not in ("jsonl", "csv"):
        raise HTTPException(status_code=400, detail="Format must be 'jsonl' or 'csv'")
```

**Valid formats:**
- `"jsonl"`: JSON Lines (one JSON object per line)
- `"csv"`: Comma-Separated Values

**Invalid format example:**
```http
POST /admin/telemetry/export?format=xml

Response:
{
  "detail": "Format must be 'jsonl' or 'csv'"
}
Status: 400 Bad Request
```

---

#### Build Output Path

```python
    output_file = f"data/exports/training_data.{format}"
```

**Examples:**
```python
format = "jsonl"
output_file = "data/exports/training_data.jsonl"

format = "csv"
output_file = "data/exports/training_data.csv"
```

**Path structure:**
```
project_root/
├── data/
│   ├── telemetry/
│   │   ├── telemetry_20251109.jsonl
│   │   ├── telemetry_20251110.jsonl
│   │   └── telemetry_20251111.jsonl
│   └── exports/
│       ├── training_data.jsonl  ← Output here
│       └── training_data.csv
```

---

#### Create Directory

```python
    os.makedirs("data/exports", exist_ok=True)
```

**Purpose:**
- Ensure `data/exports/` directory exists
- Create if doesn't exist
- Don't error if already exists

**Without this:**
```python
# If data/exports/ doesn't exist:
collector.export_training_data("data/exports/file.jsonl")
# → FileNotFoundError: [Errno 2] No such file or directory
```

**With this:**
```python
os.makedirs("data/exports", exist_ok=True)
collector.export_training_data("data/exports/file.jsonl")
# → ✅ Creates directory, then file
```

---

#### Export Data

```python
    count = collector.export_training_data(output_file, format=format)
```

**Method call:**
- `output_file`: Destination path
- `format`: "jsonl" or "csv"
- Returns: Number of records exported

**See:** `app.middleware.telemetry.export_training_data()` (explained in 02_telemetry.py.md)

---

#### Return Response

```python
    return {
        "status": "success",
        "records_exported": count,
        "file": output_file
    }
```

**Example response:**
```json
{
  "status": "success",
  "records_exported": 1425,
  "file": "data/exports/training_data.jsonl"
}
```

**Client can then:**
1. Display success message: "Exported 1425 records"
2. Download file using `/admin/telemetry/download/training_data.jsonl`

---

### JSONL Export Example

**Request:**
```http
POST /admin/telemetry/export?format=jsonl
Authorization: Bearer admin-key
```

**Output file (`training_data.jsonl`):**
```jsonl
{"prefix":"....................","suffix":"..........","completion":"...............","language":"python","model":"groq/deepseek-coder-6.7b-instruct"}
{"prefix":"...................................","suffix":".....","completion":".........................","language":"typescript","model":"groq/llama3-70b"}
{"prefix":"...........","suffix":"","completion":"........","language":"javascript","model":"groq/deepseek-coder-6.7b-instruct"}
```

**Note:** 
- Only successful completions (no errors)
- Code content replaced with dots (privacy)
- Metadata preserved (language, model, lengths)

---

### CSV Export Example

**Request:**
```http
POST /admin/telemetry/export?format=csv
Authorization: Bearer admin-key
```

**Output file (`training_data.csv`):**
```csv
timestamp,language,prefix_len,suffix_len,completion_len,model,latency_ms,success
2025-11-11T08:30:15.123,python,20,10,15,groq/deepseek-coder-6.7b-instruct,234.5,True
2025-11-11T08:31:22.456,typescript,35,5,25,groq/llama3-70b,456.7,True
2025-11-11T08:33:10.789,javascript,11,0,8,groq/deepseek-coder-6.7b-instruct,189.3,True
```

**Use cases:**
- Import into Excel/Google Sheets
- Analysis with pandas
- Data visualization

---

## 📥 Endpoint: GET `/admin/telemetry/download/{filename}`

### Purpose
**Download exported telemetry files**

### Code

```python
@router.get("/telemetry/download/{filename}", dependencies=[Depends(require_api_key)])
def download_telemetry_file(filename: str):
    """Download exported telemetry file"""
    file_path = f"data/exports/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=filename
    )
```

---

### Phân tích chi tiết

#### Path Parameter

```python
@router.get("/telemetry/download/{filename}", ...)
def download_telemetry_file(filename: str):
```

**Usage:**
```http
GET /admin/telemetry/download/training_data.jsonl
GET /admin/telemetry/download/training_data.csv
```

**FastAPI extracts:**
```python
# URL: /admin/telemetry/download/training_data.jsonl
filename = "training_data.jsonl"

# URL: /admin/telemetry/download/mydata.csv
filename = "mydata.csv"
```

---

#### Build File Path

```python
    file_path = f"data/exports/{filename}"
```

**Examples:**
```python
filename = "training_data.jsonl"
file_path = "data/exports/training_data.jsonl"

filename = "training_data.csv"
file_path = "data/exports/training_data.csv"
```

---

#### Check File Exists

```python
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
```

**Purpose:**
- Prevent errors if file doesn't exist
- Return proper HTTP 404

**Example:**
```http
GET /admin/telemetry/download/nonexistent.jsonl

Response:
{
  "detail": "File not found"
}
Status: 404 Not Found
```

---

#### Return File

```python
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=filename
    )
```

---

### FileResponse Parameters

#### `file_path`
- Path to file on server
- FastAPI reads and streams to client

#### `media_type="application/octet-stream"`
- Generic binary stream type
- Browser treats as download (not display)
- Alternative: `"application/json"`, `"text/csv"`, etc.

#### `filename=filename`
- Suggested filename for download
- Sets `Content-Disposition: attachment; filename="training_data.jsonl"`

---

### Response Headers

```http
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="training_data.jsonl"
Content-Length: 245678

<file content>
```

**Browser behavior:**
- Opens "Save As" dialog
- Suggests filename: `training_data.jsonl`

---

### Security Considerations

#### Path Traversal Attack

**Vulnerable code:**
```python
# ❌ BAD: No validation
def download(filename: str):
    return FileResponse(f"data/exports/{filename}")

# Attacker request:
GET /admin/telemetry/download/../../secrets.txt
# → file_path = "data/exports/../../secrets.txt"
# → Resolves to: "secrets.txt" (outside data/exports!)
# → Exposes sensitive files!
```

**Current code is SAFE:**
```python
# ✅ GOOD: Only files in data/exports/
file_path = f"data/exports/{filename}"
if not os.path.exists(file_path):
    raise HTTPException(404)
# Even with ../../, only serves if file actually exists in data/exports/
```

**Better mitigation:**
```python
import os.path

def download_telemetry_file(filename: str):
    # Validate filename (no path separators)
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, detail="Invalid filename")
    
    file_path = f"data/exports/{filename}"
    
    # Ensure resolved path is within data/exports/
    real_path = os.path.realpath(file_path)
    if not real_path.startswith(os.path.realpath("data/exports/")):
        raise HTTPException(403, detail="Access denied")
    
    if not os.path.exists(file_path):
        raise HTTPException(404, detail="File not found")
    
    return FileResponse(file_path, ...)
```

---

## 📊 Complete Workflow Example

### Step 1: Check Statistics

```bash
curl -X GET "http://localhost:8000/admin/telemetry/stats" \
  -H "Authorization: Bearer admin-key"
```

**Response:**
```json
{
  "total_requests": 1500,
  "successful_requests": 1425,
  "languages": {"python": 800, "typescript": 500, ...}
}
```

---

### Step 2: Export Data

```bash
curl -X POST "http://localhost:8000/admin/telemetry/export?format=jsonl" \
  -H "Authorization: Bearer admin-key"
```

**Response:**
```json
{
  "status": "success",
  "records_exported": 1425,
  "file": "data/exports/training_data.jsonl"
}
```

---

### Step 3: Download File

```bash
curl -X GET "http://localhost:8000/admin/telemetry/download/training_data.jsonl" \
  -H "Authorization: Bearer admin-key" \
  -o training_data.jsonl
```

**Output:**
```
  % Total    % Received
100  245k  100  245k    0     0   245k      0  0:00:01  0:00:01 --:--:--  245k
```

**File downloaded:** `training_data.jsonl` (245 KB)

---

### Step 4: Use for Training

```bash
# Python script
import json

# Load exported data
with open('training_data.jsonl', 'r') as f:
    data = [json.loads(line) for line in f]

print(f"Loaded {len(data)} training examples")

# Filter by language
python_examples = [d for d in data if d['language'] == 'python']
print(f"Python examples: {len(python_examples)}")

# Prepare for fine-tuning
# ...
```

---

## 💡 Key Points cho thuyết trình

### 1. Admin Endpoints Purpose

**Separate from user endpoints:**
```
User endpoints:        Admin endpoints:
/complete             /admin/telemetry/stats
/complete_stream      /admin/telemetry/export
/health               /admin/telemetry/download
```

**Why separate?**
- Clear security boundary
- Different authentication needs
- Easier to document
- Can deploy separately (microservices)

---

### 2. Authentication Required

**All admin endpoints protected:**
```python
@router.get("/telemetry/stats", dependencies=[Depends(require_api_key)])
```

**Security implications:**
- Only authorized admins can access
- Prevents data leakage
- Audit trail (who accessed when)

---

### 3. Export Formats

**JSONL vs CSV:**

| Format | Use Case | Advantages |
|--------|----------|------------|
| **JSONL** | ML training, API processing | Nested data, preserves types |
| **CSV** | Excel, data analysis | Simple, widely supported |

**Example comparison:**

**JSONL:**
```json
{"prefix":"...", "language":"python", "model":"groq/deepseek"}
```

**CSV:**
```csv
prefix,language,model
...,python,groq/deepseek
```

---

### 4. File Download Pattern

**FileResponse benefits:**
- Automatic streaming (memory-efficient)
- Proper headers (Content-Disposition)
- Browser-friendly (triggers download)

**Alternative (BAD):**
```python
# ❌ Load entire file into memory
with open(file_path, 'r') as f:
    content = f.read()
return {"content": content}  # JSON (inefficient for large files!)
```

**FileResponse (GOOD):**
```python
# ✅ Stream file chunk by chunk
return FileResponse(file_path)  # Memory-efficient!
```

---

### 5. Directory Management

**Safe directory creation:**
```python
os.makedirs("data/exports", exist_ok=True)
```

**Why `exist_ok=True`?**
```python
# Without exist_ok:
os.makedirs("data/exports")  # First call: OK
os.makedirs("data/exports")  # Second call: FileExistsError!

# With exist_ok:
os.makedirs("data/exports", exist_ok=True)  # OK
os.makedirs("data/exports", exist_ok=True)  # OK (idempotent)
```

---

## 🧪 Test Cases

### Test 1: Get statistics

```python
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch

client = TestClient(app)

# Mock telemetry stats
mock_stats = {
    "total_requests": 100,
    "successful_requests": 95,
    "failed_requests": 5
}

with patch('app.middleware.telemetry.get_telemetry_collector') as mock_collector:
    mock_collector.return_value.get_stats.return_value = mock_stats
    
    response = client.get(
        "/admin/telemetry/stats",
        headers={"Authorization": "Bearer test-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] == 100
    assert data["successful_requests"] == 95
```

---

### Test 2: Export telemetry (JSONL)

```python
import os

with patch('app.middleware.telemetry.get_telemetry_collector') as mock_collector:
    mock_collector.return_value.export_training_data.return_value = 50
    
    response = client.post(
        "/admin/telemetry/export?format=jsonl",
        headers={"Authorization": "Bearer test-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["records_exported"] == 50
    assert data["file"] == "data/exports/training_data.jsonl"
```

---

### Test 3: Export invalid format

```python
response = client.post(
    "/admin/telemetry/export?format=xml",
    headers={"Authorization": "Bearer test-key"}
)

assert response.status_code == 400
assert "Format must be" in response.json()["detail"]
```

---

### Test 4: Download file (success)

```python
import tempfile
import os

# Create temporary test file
with tempfile.TemporaryDirectory() as tmpdir:
    test_file = os.path.join(tmpdir, "test.jsonl")
    with open(test_file, 'w') as f:
        f.write('{"test": "data"}\n')
    
    with patch('app.routers.admin.f"data/exports/{filename}"', test_file):
        response = client.get(
            "/admin/telemetry/download/test.jsonl",
            headers={"Authorization": "Bearer test-key"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert "test.jsonl" in response.headers["content-disposition"]
```

---

### Test 5: Download file not found

```python
response = client.get(
    "/admin/telemetry/download/nonexistent.jsonl",
    headers={"Authorization": "Bearer test-key"}
)

assert response.status_code == 404
assert "not found" in response.json()["detail"].lower()
```

---

### Test 6: Unauthorized access

```python
# No Authorization header
response = client.get("/admin/telemetry/stats")
assert response.status_code == 401

# Invalid token
response = client.get(
    "/admin/telemetry/stats",
    headers={"Authorization": "Bearer invalid"}
)
assert response.status_code == 401
```

---

## 🔧 Usage Examples

### Admin Dashboard (React)

```typescript
import React, { useState, useEffect } from 'react';

function AdminDashboard() {
    const [stats, setStats] = useState(null);
    const [exporting, setExporting] = useState(false);
    
    useEffect(() => {
        loadStats();
    }, []);
    
    async function loadStats() {
        const response = await fetch('/admin/telemetry/stats', {
            headers: {'Authorization': 'Bearer admin-key'}
        });
        const data = await response.json();
        setStats(data);
    }
    
    async function exportData(format: 'jsonl' | 'csv') {
        setExporting(true);
        try {
            const response = await fetch(`/admin/telemetry/export?format=${format}`, {
                method: 'POST',
                headers: {'Authorization': 'Bearer admin-key'}
            });
            const data = await response.json();
            
            alert(`Exported ${data.records_exported} records`);
            
            // Download file
            const downloadUrl = `/admin/telemetry/download/training_data.${format}`;
            window.open(downloadUrl, '_blank');
        } finally {
            setExporting(false);
        }
    }
    
    if (!stats) return <div>Loading...</div>;
    
    return (
        <div>
            <h1>Admin Dashboard</h1>
            
            <div className="stats-grid">
                <div className="stat-card">
                    <h3>Total Requests</h3>
                    <p>{stats.total_requests}</p>
                </div>
                <div className="stat-card">
                    <h3>Success Rate</h3>
                    <p>{(stats.successful_requests / stats.total_requests * 100).toFixed(1)}%</p>
                </div>
                <div className="stat-card">
                    <h3>Avg Latency</h3>
                    <p>{stats.avg_latency_ms.toFixed(0)}ms</p>
                </div>
            </div>
            
            <div className="export-section">
                <h2>Export Training Data</h2>
                <button onClick={() => exportData('jsonl')} disabled={exporting}>
                    Export JSONL
                </button>
                <button onClick={() => exportData('csv')} disabled={exporting}>
                    Export CSV
                </button>
            </div>
            
            <div className="languages">
                <h2>Language Distribution</h2>
                <ul>
                    {Object.entries(stats.languages).map(([lang, count]) => (
                        <li key={lang}>
                            {lang}: {count} ({(count / stats.total_requests * 100).toFixed(1)}%)
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
}
```

---

### Python Analysis Script

```python
import requests
import pandas as pd

# Admin credentials
headers = {'Authorization': 'Bearer admin-key'}
base_url = 'http://localhost:8000/admin'

# 1. Get statistics
stats = requests.get(f'{base_url}/telemetry/stats', headers=headers).json()
print(f"Total requests: {stats['total_requests']}")
print(f"Success rate: {stats['successful_requests'] / stats['total_requests'] * 100:.1f}%")

# 2. Export CSV
export_resp = requests.post(
    f'{base_url}/telemetry/export?format=csv',
    headers=headers
).json()
print(f"Exported {export_resp['records_exported']} records")

# 3. Download and analyze
download_url = f"{base_url}/telemetry/download/training_data.csv"
response = requests.get(download_url, headers=headers)
with open('training_data.csv', 'wb') as f:
    f.write(response.content)

# 4. Analysis with pandas
df = pd.read_csv('training_data.csv')
print(f"\nDataFrame shape: {df.shape}")
print(f"\nLanguage distribution:")
print(df['language'].value_counts())
print(f"\nAverage latency by language:")
print(df.groupby('language')['latency_ms'].mean())
```

---

**File này hoàn tất!** Tiếp theo: `feedback.py`. Tiếp tục không? 🚀

