# Giải thích chi tiết: `server/app/routers/health.py`

## 📋 Mục đích của file

File này implement **Health Check Endpoints** để:
1. **Verify API connectivity** với Groq API
2. **List available models** từ Groq
3. **Monitor service status** (health checks)
4. **Provide debugging info** về configuration

---

## 🔍 Phân tích từng phần

### Import statements

```python
from fastapi import APIRouter, HTTPException
import requests

from app.core.config import settings
```

**Giải thích:**

- `APIRouter`: FastAPI router để group endpoints
- `HTTPException`: Raise HTTP errors (4xx, 5xx)
- `requests`: HTTP client library (synchronous)
- `settings`: Config values (GROQ_API_KEY, GROQ_MODEL)

---

## 🛠️ Router Setup

```python
router = APIRouter(prefix="", tags=["health"])
```

**Parameters:**

#### `prefix=""`
- No prefix (endpoints at root level)
- URLs: `/health`, `/models` (not `/api/health`)

#### `tags=["health"]`
- OpenAPI/Swagger grouping
- Docs UI groups these endpoints together

---

## 🏥 Endpoint: GET `/health`

### Purpose
Health check endpoint để verify service status và Groq API connectivity

### Code

```python
@router.get("/health")
def health():
    """
    Health check - verifies Groq API connectivity.
    """
    ok = True
    models = []
```

---

### Phân tích chi tiết

#### `@router.get("/health")`

**Decorator:**
- HTTP method: `GET`
- Path: `/health`
- No authentication required (public endpoint)

**Use cases:**
- Load balancer health checks
- Kubernetes liveness/readiness probes
- Monitoring systems (Prometheus, Grafana)

---

#### Initialize variables

```python
    ok = True
    models = []
```

**Defaults:**
- `ok = True`: Assume healthy (optimistic)
- `models = []`: Empty list (will populate if API works)

---

### Check Groq API Key

```python
    if settings.GROQ_API_KEY:
```

**Logic:**
- If API key configured → test connection
- If no API key → mark as degraded

**Example:**
```python
# .env file:
GROQ_API_KEY=gsk_abc123...  # ✅ Will test connection

# No GROQ_API_KEY:
# → ok = False (degraded)
```

---

### Test Groq API Connection

```python
        try:
            # Test Groq API connection
            resp = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                timeout=5
            )
```

---

#### API Endpoint

**URL:**
```
https://api.groq.com/openai/v1/models
```

**Purpose:**
- List available models
- Lightweight endpoint (fast response)
- Verifies API key validity

---

#### Authorization Header

```python
headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
```

**Format:**
```
Authorization: Bearer gsk_abc123xyz...
```

**Bearer token pattern:**
- Standard OAuth 2.0 format
- Common in REST APIs

---

#### Timeout

```python
timeout=5
```

**Purpose:**
- Don't wait forever
- Health check should be fast
- 5 seconds = reasonable for external API

**Without timeout:**
```python
resp = requests.get(url)  # ❌ Might hang forever!
# If Groq API down, health check hangs

resp = requests.get(url, timeout=5)  # ✅ Max 5s wait
```

---

### Parse Response

```python
            if resp.ok:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", [])]
            else:
                ok = False
```

---

#### `resp.ok`

**Property:**
- `True` if status code 200-299 (success)
- `False` if 400-599 (error)

**Example:**
```python
# Status 200:
resp.status_code = 200
resp.ok  # → True ✅

# Status 404:
resp.status_code = 404
resp.ok  # → False ❌
```

---

#### Parse JSON Response

```python
data = resp.json()
models = [m.get("id") for m in data.get("data", [])]
```

**Expected response format:**
```json
{
  "object": "list",
  "data": [
    {"id": "llama-3.3-70b-versatile", "object": "model", ...},
    {"id": "mixtral-8x7b-32768", "object": "model", ...},
    {"id": "deepseek-r1-distill-llama-70b", "object": "model", ...}
  ]
}
```

**Extract model IDs:**
```python
# data = {"data": [{"id": "llama-3.3-70b-versatile"}, ...]}
# data.get("data", []) → List of model objects
# m.get("id") for each model → Extract ID
# Result: ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", ...]
```

---

#### List comprehension breakdown

```python
models = [m.get("id") for m in data.get("data", [])]
```

**Step by step:**
```python
# Step 1: Get data list
data.get("data", [])
# → [{"id": "model1"}, {"id": "model2"}]

# Step 2: Loop each model
for m in data.get("data", []):
    # m = {"id": "model1"}
    # m = {"id": "model2"}

# Step 3: Extract ID
m.get("id")
# → "model1"
# → "model2"

# Step 4: Collect in list
# → ["model1", "model2"]
```

---

### Handle Errors

```python
        except Exception:
            ok = False
    else:
        ok = False
```

**Catch-all exception:**
```python
# Possible exceptions:
# - requests.exceptions.Timeout (timeout exceeded)
# - requests.exceptions.ConnectionError (network issue)
# - requests.exceptions.RequestException (HTTP error)
# - json.JSONDecodeError (invalid JSON)
# All → mark as unhealthy
```

**No API key:**
```python
else:
    ok = False
```

---

### Return Response

```python
    return {
        "status": "ok" if ok else "degraded",
        "model": settings.GROQ_MODEL,
        "available_models": models,
    }
```

---

### Response Fields

#### `"status"`

**Values:**
- `"ok"`: Groq API reachable, API key valid
- `"degraded"`: Groq API unreachable or invalid API key

**Example:**
```json
{
  "status": "ok",
  "model": "llama-3.3-70b-versatile",
  "available_models": [
    "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768",
    "deepseek-r1-distill-llama-70b"
  ]
}
```

---

#### `"model"`

**Current configured model:**
```python
# .env:
GROQ_MODEL=llama-3.3-70b-versatile

# Response:
"model": "llama-3.3-70b-versatile"
```

**Purpose:**
- Show which model is being used
- Verify configuration

---

#### `"available_models"`

**List of models from Groq:**
- Empty if API unreachable: `[]`
- Populated on success: `["llama-3.3-70b-versatile", ...]`

**Use case:**
```python
# Check if configured model is available:
response = requests.get("/health").json()
if response["model"] in response["available_models"]:
    print("✅ Model is available")
else:
    print("❌ Model not available!")
```

---

## 📋 Endpoint: GET `/models`

### Purpose
List all available models từ Groq API

### Code

```python
@router.get("/models")
def models():
    """
    List available Groq models.
    """
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
```

---

### Check API Key

```python
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
```

**HTTPException:**
- Status code: `500` (Internal Server Error)
- Detail: Error message for client

**Response:**
```json
{
  "detail": "GROQ_API_KEY not configured"
}
```

**Why 500?**
- Configuration issue (server problem)
- Not client's fault
- 4xx = client error, 5xx = server error

---

### Query Groq API

```python
    try:
        resp = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            timeout=5
        )
        resp.raise_for_status()
        return resp.json()
```

---

#### `resp.raise_for_status()`

**Purpose:**
- Raise exception if status code is error (4xx, 5xx)
- No exception if success (2xx)

**Example:**
```python
# Status 200:
resp.status_code = 200
resp.raise_for_status()  # No exception ✅

# Status 404:
resp.status_code = 404
resp.raise_for_status()  # ❌ Raises requests.exceptions.HTTPError
```

---

#### Return JSON directly

```python
return resp.json()
```

**Full Groq response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "llama-3.3-70b-versatile",
      "object": "model",
      "created": 1234567890,
      "owned_by": "Meta",
      "active": true,
      "context_window": 8192,
      "public_apps": null
    },
    {
      "id": "mixtral-8x7b-32768",
      "object": "model",
      "created": 1234567890,
      "owned_by": "Mistral",
      "active": true,
      "context_window": 32768,
      "public_apps": null
    }
  ]
}
```

---

### Handle Errors

```python
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot query Groq models: {e}") from e
```

---

#### Status Code 502

**502 Bad Gateway:**
- Server acting as gateway/proxy
- Got invalid response from upstream server
- Here: Groq API returned error

**Common causes:**
```python
# Timeout:
requests.exceptions.Timeout
# → 502: Cannot query Groq models: timeout exceeded

# Connection error:
requests.exceptions.ConnectionError
# → 502: Cannot query Groq models: connection refused

# HTTP error:
resp.status_code = 429  # Rate limit
# → 502: Cannot query Groq models: 429 Rate Limit
```

---

#### `from e`

**Exception chaining:**
```python
raise HTTPException(...) from e
```

**Purpose:**
- Preserve original exception traceback
- Better debugging

**Example traceback:**
```
Traceback (most recent call last):
  ...
  requests.exceptions.Timeout: timeout exceeded
  
The above exception was the direct cause of the following exception:
  
HTTPException: 502 Cannot query Groq models: timeout exceeded
```

---

## 📊 Diagram: Health Check Flow

```
┌─────────────────────────────────────────────────────┐
│                Client Request                        │
│  GET /health                                        │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│              health() function                       │
│                                                     │
│  1. Check if GROQ_API_KEY exists                    │
│     - Yes → Continue                                │
│     - No → ok = False, skip API test                │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓ (if API key exists)
┌─────────────────────────────────────────────────────┐
│         Test Groq API Connection                     │
│  requests.get(                                      │
│    "https://api.groq.com/openai/v1/models",        │
│    headers={"Authorization": "Bearer ..."},         │
│    timeout=5                                        │
│  )                                                  │
└────────────────────┬────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
          ↓ Success (2xx)       ↓ Failure (4xx/5xx/timeout)
┌─────────────────────┐   ┌─────────────────────┐
│  resp.ok = True     │   │  resp.ok = False    │
│  Parse JSON:        │   │  or Exception       │
│  - Extract model    │   │  ok = False         │
│    IDs from data    │   │  models = []        │
│  ok = True          │   └─────────┬───────────┘
│  models = [...]     │             │
└──────────┬──────────┘             │
           │                        │
           └────────────┬───────────┘
                        ↓
           ┌────────────────────────┐
           │   Return Response      │
           │  {                     │
           │    "status": "ok" or   │
           │              "degraded"│
           │    "model": "...",     │
           │    "available_models": │
           │        [...]           │
           │  }                     │
           └────────────────────────┘
```

---

## 💡 Use Cases

### 1. Kubernetes Health Probe

**Liveness probe:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
```

**Purpose:**
- If `/health` returns error → restart pod
- Ensures service stays healthy

---

### 2. Load Balancer Health Check

**AWS Application Load Balancer:**
```
Health check path: /health
Healthy threshold: 2 consecutive successes
Unhealthy threshold: 3 consecutive failures
```

**Purpose:**
- Route traffic only to healthy instances
- Remove unhealthy instances from pool

---

### 3. Monitoring Dashboard

**Prometheus metrics:**
```python
# Scrape /health endpoint every 15s
# If status = "ok" → health_status = 1
# If status = "degraded" → health_status = 0

# Alert if health_status = 0 for > 5 minutes
```

---

### 4. Debugging Configuration

**Check model availability:**
```bash
# Test health endpoint
curl http://localhost:8000/health

# Response shows:
# - Current model: llama-3.3-70b-versatile
# - Available models: [...]

# Verify model is in available list
```

---

### 5. Model Discovery

**List all models:**
```bash
curl http://localhost:8000/models

# Returns full model details:
# - Model IDs
# - Context windows
# - Owners
```

**Use in frontend:**
```typescript
// Dropdown to select model
const response = await fetch('/models');
const data = await response.json();
const modelIds = data.data.map(m => m.id);

// Show in UI:
// <select>
//   <option>llama-3.3-70b-versatile</option>
//   <option>mixtral-8x7b-32768</option>
// </select>
```

---

## 🧪 Test Cases

### Test 1: Health check success

```python
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, Mock

client = TestClient(app)

# Mock successful Groq API response
mock_response = Mock()
mock_response.ok = True
mock_response.json.return_value = {
    "data": [
        {"id": "llama-3.3-70b-versatile"},
        {"id": "mixtral-8x7b-32768"}
    ]
}

with patch('requests.get', return_value=mock_response):
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "llama-3.3-70b-versatile" in data["available_models"]
```

---

### Test 2: Health check degraded (API failure)

```python
import requests

# Mock timeout exception
with patch('requests.get', side_effect=requests.exceptions.Timeout):
    response = client.get("/health")
    
    assert response.status_code == 200  # Still returns 200!
    data = response.json()
    assert data["status"] == "degraded"  # But status is degraded
    assert data["available_models"] == []
```

**Note:**
- Health endpoint always returns 200
- Status field indicates health: "ok" or "degraded"

---

### Test 3: Models endpoint success

```python
mock_response = Mock()
mock_response.json.return_value = {
    "object": "list",
    "data": [{"id": "model1"}, {"id": "model2"}]
}
mock_response.raise_for_status = Mock()  # No exception

with patch('requests.get', return_value=mock_response):
    response = client.get("/models")
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 2
```

---

### Test 4: Models endpoint error (no API key)

```python
from app.core.config import settings

# Temporarily remove API key
original_key = settings.GROQ_API_KEY
settings.GROQ_API_KEY = None

response = client.get("/models")

assert response.status_code == 500
assert "GROQ_API_KEY not configured" in response.json()["detail"]

# Restore
settings.GROQ_API_KEY = original_key
```

---

### Test 5: Models endpoint error (API failure)

```python
with patch('requests.get', side_effect=requests.exceptions.ConnectionError):
    response = client.get("/models")
    
    assert response.status_code == 502  # Bad Gateway
    assert "Cannot query Groq models" in response.json()["detail"]
```

---

## 💡 Key Points cho thuyết trình

### 1. Health vs Models Endpoints

**Comparison:**

| Aspect | `/health` | `/models` |
|--------|-----------|-----------|
| **Purpose** | Service health check | List available models |
| **On error** | Returns 200 with "degraded" | Returns 502 error |
| **Use case** | Load balancers, probes | User selection, debugging |
| **Authentication** | Public | Public |

---

### 2. Why `/health` always returns 200?

**Design pattern:**
```python
# ❌ Bad: Health check returns error
GET /health → 500
# Load balancer removes instance immediately!

# ✅ Good: Health check returns 200 with status
GET /health → 200 {"status": "degraded"}
# Load balancer can implement smart logic:
# - "ok" → route traffic
# - "degraded" → route traffic but alert
# - Timeout → remove instance
```

---

### 3. Timeout Importance

**Without timeout:**
```python
requests.get(url)  # Hangs 60+ seconds if API down
# Health check takes 60s!
# Load balancer marks as unhealthy
```

**With timeout:**
```python
requests.get(url, timeout=5)  # Max 5s
# Health check fast even on failure
# Quick feedback
```

---

### 4. Error Codes

**502 Bad Gateway:**
- Used when upstream service fails
- Appropriate for Groq API errors

**500 Internal Server Error:**
- Used for configuration issues
- Our fault, not external service

---

### 5. Model Information Use Cases

**Operations:**
- Verify configured model exists
- Monitor model availability
- Track Groq API status

**Development:**
- Test different models
- Model selection UI
- Capability discovery

---

## 🔧 Usage Examples

### Example 1: Health Check in Load Balancer

```nginx
# Nginx config
upstream backend {
    server localhost:8000;
    
    # Health check
    health_check uri=/health
                 interval=10s
                 fails=3
                 passes=2;
}
```

---

### Example 2: Monitoring Script

```bash
#!/bin/bash
# monitor.sh - Check service health

HEALTH=$(curl -s http://localhost:8000/health | jq -r '.status')

if [ "$HEALTH" != "ok" ]; then
    echo "⚠️  Service degraded! Sending alert..."
    # Send alert to Slack/email
    curl -X POST https://hooks.slack.com/... \
        -d '{"text": "AI Coder service is degraded!"}'
fi
```

---

### Example 3: Model Selection UI

```typescript
// Frontend code
async function loadAvailableModels() {
    const response = await fetch('/models');
    const data = await response.json();
    
    const select = document.getElementById('model-select');
    data.data.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.text = `${model.id} (${model.context_window} tokens)`;
        select.appendChild(option);
    });
}
```

---

### Example 4: Startup Verification

```python
# main.py startup event
import requests

@app.on_event("startup")
async def verify_groq_connection():
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        data = response.json()
        if data["status"] == "ok":
            logger.info(f"✅ Groq API connected. Model: {data['model']}")
            logger.info(f"Available models: {len(data['available_models'])}")
        else:
            logger.warning("⚠️  Groq API not available (degraded status)")
    except Exception as e:
        logger.error(f"❌ Cannot verify Groq connection: {e}")
```

---

**File này hoàn tất!** Tiếp theo: `completions.py` (main endpoint - 162 lines). Tiếp tục không? 🚀

