# Giải thích chi tiết: Deployment trên Render.com

## 📋 Tổng quan

**BTL AI Coder** được deploy lên **Render.com** - Platform-as-a-Service (PaaS) miễn phí!

### Kiến trúc Deployment

```
┌─────────────────────────────────────────────────────────┐
│              VS Code Extension (Local)                  │
│  - Chạy trên máy user                                  │
│  - TypeScript compiled                                 │
│  - Gọi API qua HTTPS                                   │
└────────────┬────────────────────────────────────────────┘
             │ HTTPS Request
             ↓
┌─────────────────────────────────────────────────────────┐
│           Render.com (Cloud Platform)                   │
│  ┌───────────────────────────────────────────────────┐ │
│  │  FastAPI Server (Python)                          │ │
│  │  - URL: btl-python-r9kz.onrender.com              │ │
│  │  - Auto SSL/HTTPS                                 │ │
│  │  - Auto-deploy từ Git                             │ │
│  │  - Free tier (512MB RAM)                          │ │
│  └───────────────┬───────────────────────────────────┘ │
│                  │                                       │
│                  ↓                                       │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Environment Variables                            │ │
│  │  - GROQ_API_KEY                                   │ │
│  │  - API_KEY (5conmeo)                              │ │
│  │  - MODEL (qwen2.5-coder:7b)                       │ │
│  └───────────────────────────────────────────────────┘ │
└────────────┬────────────────────────────────────────────┘
             │ API Call
             ↓
┌─────────────────────────────────────────────────────────┐
│              Groq Cloud API                             │
│  - LLM inference (fast!)                               │
│  - Model: qwen2.5-coder:7b                             │
│  - Free tier: 30 requests/min                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 File: `server/render.yaml`

### Mục đích
**Infrastructure as Code (IaC)** - Cấu hình deployment cho Render.com

### Nội dung chi tiết

```yaml
services:
  - type: web
    name: btl-python-server
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: OLLAMA_URL
        sync: false
      - key: OLLAMA_API_KEY
        sync: false
      - key: MODEL
        value: qwen2.5-coder:7b
      - key: API_KEY
        value: 5conmeo
      - key: NUM_CTX
        value: 4096
      - key: POSTPROCESS_ENABLED
        value: true
      - key: ALLOW_ORIGINS
        value: "*"
```

---

### Phân tích từng phần

#### Service Type

```yaml
services:
  - type: web
```

**`type: web`** - Web service (chạy 24/7, nhận HTTP requests)

**Các loại khác:**
- `worker` - Background job (không nhận HTTP)
- `cron` - Scheduled task (chạy định kỳ)
- `private-service` - Internal service (không public)

---

#### Service Name

```yaml
name: btl-python-server
```

**Tên service** hiển thị trong Render dashboard

**URL tự động:** `btl-python-server-xxxx.onrender.com`

---

#### Runtime

```yaml
runtime: python
```

**Python environment** với các features:
- Python 3.11+ (latest stable)
- pip package manager
- Virtualenv tự động
- Auto-detect Python version từ `runtime.txt` (nếu có)

---

#### Build Command

```yaml
buildCommand: pip install -r requirements.txt
```

**Chạy khi deploy** (build phase)

**Process:**
```bash
# Render tự động chạy:
cd server/
pip install -r requirements.txt

# Install các packages:
# - fastapi>=0.104.1
# - uvicorn[standard]>=0.24.0
# - httpx>=0.25.0
# - pydantic-settings>=2.0.0
# - requests>=2.31.0
# - groq>=0.4.0
# - black>=23.0.0
# - autopep8>=2.0.0
```

**Build log example:**
```
Collecting fastapi>=0.104.1
  Downloading fastapi-0.104.1-py3-none-any.whl (92 kB)
Collecting uvicorn[standard]>=0.24.0
  Downloading uvicorn-0.24.0-py3-none-any.whl (59 kB)
...
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 ...
Build complete! ✅
```

---

#### Start Command

```yaml
startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Chạy khi start service** (run phase)

**Breakdown:**

**`uvicorn`** - ASGI server (production-ready)

**`app.main:app`**
- `app.main` - Module path (`server/app/main.py`)
- `:app` - FastAPI instance variable name

**`--host 0.0.0.0`**
- Bind to all interfaces
- Accept connections from internet
- Required for Render (không dùng `127.0.0.1`!)

**`--port $PORT`**
- `$PORT` - Environment variable từ Render
- Render tự động assign port (thường là 10000)
- **Phải dùng $PORT** (không hardcode!)

**Why not `--reload`?**
```bash
# Development:
uvicorn app.main:app --reload  # Auto-reload on code change

# Production (Render):
uvicorn app.main:app  # No reload (stability + performance)
```

---

#### Environment Variables

```yaml
envVars:
  - key: OLLAMA_URL
    sync: false
  - key: OLLAMA_API_KEY
    sync: false
```

**`sync: false`** - Không sync từ Git (nhập manual trong dashboard)

**Why?**
- Sensitive data (API keys)
- Different per environment (dev/staging/prod)
- Security (không commit vào Git)

---

##### OLLAMA_URL

```yaml
- key: OLLAMA_URL
  sync: false
```

**Optional** - URL cho Ollama local server

**Use cases:**
- Self-hosted Ollama (qua Tailscale VPN)
- Local development
- Custom inference server

**Example values:**
```bash
# Tailscale (remote Ollama):
OLLAMA_URL=http://100.64.0.1:11434

# Local (same machine):
OLLAMA_URL=http://127.0.0.1:11434

# Not set (use Groq instead):
OLLAMA_URL=  # Empty or không set
```

---

##### OLLAMA_API_KEY

```yaml
- key: OLLAMA_API_KEY
  sync: false
```

**Optional** - API key for Ollama (nếu có authentication)

**Standard Ollama:** Không cần API key (local server)

**Enterprise Ollama:** Có thể require authentication

---

##### MODEL

```yaml
- key: MODEL
  value: qwen2.5-coder:7b
```

**`value: ...`** - Có default value (không cần nhập manual)

**Qwen 2.5 Coder 7B:**
- Specialized for code generation
- 7 billion parameters
- Balance giữa speed và quality
- Support Python, C++, JavaScript, etc.

**Alternatives:**
```yaml
# Groq models:
MODEL=llama-3.1-70b-versatile  # General purpose
MODEL=codellama-34b-instruct   # Meta's CodeLLaMA
MODEL=mixtral-8x7b-32768       # Large context

# Ollama models:
MODEL=qwen2.5-coder:7b         # Default
MODEL=codellama:13b            # Larger CodeLLaMA
MODEL=deepseek-coder:6.7b      # DeepSeek
```

---

##### API_KEY

```yaml
- key: API_KEY
  value: 5conmeo
```

**Internal API key** - Protect server endpoints

**Usage trong code:**
```python
# server/app/core/security.py
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials):
    if credentials.credentials != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

**Client request:**
```typescript
// VS Code extension
fetch('https://btl-python-r9kz.onrender.com/complete', {
  headers: {
    'Authorization': 'Bearer 5conmeo'
  }
})
```

**Security note:** Production nên dùng strong key (UUID, random string)

---

##### NUM_CTX

```yaml
- key: NUM_CTX
  value: 4096
```

**Context window size** - Số token tối đa cho LLM

**4096 tokens ≈ 3000 words ≈ 200-300 lines of code**

**Trade-offs:**

**Smaller (2048):**
- ✅ Faster inference
- ✅ Less memory
- ✅ Lower cost
- ❌ Less context

**Larger (8192):**
- ✅ More context
- ✅ Better completions
- ❌ Slower
- ❌ More memory
- ❌ Higher cost (some APIs)

**Optimal for code:** 4096-8192

---

##### POSTPROCESS_ENABLED

```yaml
- key: POSTPROCESS_ENABLED
  value: true
```

**Enable postprocessing** của LLM outputs

**Postprocessing steps (từ `server/app/core/postprocess.py`):**

1. **Strip markdown fences**
```python
# LLM output:
"""
```python
def add(a, b):
    return a + b
```
"""

# After postprocess:
"def add(a, b):\n    return a + b"
```

2. **Remove comments**
```python
# LLM output:
"# Here's the implementation:\ndef add(a, b):"

# After:
"def add(a, b):"
```

3. **Format code (black/clang-format)**
```python
# LLM output (messy):
"def add(a,b):return a+b"

# After black:
"def add(a, b):\n    return a + b"
```

4. **Remove duplicate newlines**
```python
# LLM output:
"def add(a, b):\n\n\n    return a + b"

# After:
"def add(a, b):\n    return a + b"
```

**When to disable:**
```yaml
POSTPROCESS_ENABLED=false
```
- Debugging (see raw LLM output)
- Custom formatting rules
- Performance testing

---

##### ALLOW_ORIGINS

```yaml
- key: ALLOW_ORIGINS
  value: "*"
```

**CORS configuration** - Which origins can call API

**`"*"`** - Allow all origins (public API)

**Security considerations:**

**Development:**
```yaml
ALLOW_ORIGINS=*  # Allow all
```

**Production (locked down):**
```yaml
ALLOW_ORIGINS=https://myapp.com,https://app.mycompany.com
```

**VS Code extension:**
```yaml
ALLOW_ORIGINS=vscode-webview://*
```

**Current setup:** `*` vì extension chạy local (không có fixed origin)

---

## 📁 File: `server/Procfile`

### Mục đích
**Heroku-style process file** (Render cũng support)

### Nội dung

```plaintext
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Format:** `<process-type>: <command>`

**`web:`** - Web process (nhận HTTP traffic)

**Render behavior:**
- Đọc `Procfile` nếu không có `render.yaml`
- `render.yaml` override `Procfile` nếu cả 2 tồn tại
- Current project: Dùng `render.yaml` (Procfile là backup)

---

## 📁 File: `server/requirements.txt`

### Mục đích
**Python dependencies** - Packages cần install

### Nội dung

```pip-requirements
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
httpx>=0.25.0
pydantic-settings>=2.0.0
requests>=2.31.0
groq>=0.4.0
black>=23.0.0
autopep8>=2.0.0
```

---

### Phân tích Dependencies

#### FastAPI

```
fastapi>=0.104.1
```

**Modern web framework**
- ✅ Async/await support
- ✅ Auto OpenAPI docs
- ✅ Type hints validation
- ✅ High performance

**Version:** `>=0.104.1` (Oct 2023+)
- Latest security patches
- New features (WebSocket improvements)
- Bug fixes

---

#### Uvicorn

```
uvicorn[standard]>=0.24.0
```

**ASGI server** - Production-ready

**`[standard]`** extra includes:
- `uvloop` - Fast event loop (2-4x faster than asyncio)
- `httptools` - Fast HTTP parsing (C extension)
- `websockets` - WebSocket support

**Alternative (minimal):**
```
uvicorn>=0.24.0  # No extra dependencies
```

---

#### HTTPX

```
httpx>=0.25.0
```

**Modern HTTP client** - Requests successor

**Features:**
- ✅ Async support (`await httpx.get(...)`)
- ✅ HTTP/2
- ✅ Connection pooling
- ✅ Timeouts
- ✅ Retries

**Usage trong project:**
```python
# server/app/core/http.py
async def fetch_with_retry(url: str, max_retries: int = 3):
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                resp = await client.get(url, timeout=10.0)
                return resp
            except httpx.TimeoutException:
                continue
```

---

#### Pydantic Settings

```
pydantic-settings>=2.0.0
```

**Configuration management** với Pydantic v2

**Usage:**
```python
# server/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GROQ_API_KEY: str
    MODEL: str = "qwen2.5-coder:7b"
    
    class Config:
        env_file = ".env"
```

**Pydantic v2 changes:**
- Split `pydantic-settings` từ `pydantic` core
- Faster validation
- Better type hints

---

#### Requests

```
requests>=2.31.0
```

**Classic HTTP client** - Synchronous

**Why include khi có httpx?**
- Some libraries depend on `requests`
- Fallback cho non-async code
- Groq SDK might use it internally

**Usage:**
```python
# Simple sync request:
import requests
resp = requests.get('https://api.groq.com/models')
```

---

#### Groq

```
groq>=0.4.0
```

**Official Groq Python SDK**

**Features:**
- ✅ OpenAI-compatible API
- ✅ Streaming support
- ✅ Error handling
- ✅ Automatic retries

**Usage:**
```python
# server/app/services/groq.py
from groq import Groq

client = Groq(api_key=settings.GROQ_API_KEY)

response = client.chat.completions.create(
    model="qwen2.5-coder:7b",
    messages=[{"role": "user", "content": "Write Python code"}],
    stream=True
)
```

---

#### Black

```
black>=23.0.0
```

**Python code formatter** - Uncompromising

**Features:**
- ✅ Consistent formatting (PEP 8)
- ✅ Fast (Rust-based parser)
- ✅ 88 character line length (default)

**Usage trong project:**
```python
# server/app/core/formatter.py
import black

def format_python_code(code: str) -> str:
    try:
        formatted = black.format_str(code, mode=black.Mode())
        return formatted
    except black.NothingChanged:
        return code
```

**Example:**
```python
# Before:
"def add(a,b):return a+b"

# After black:
"def add(a, b):\n    return a + b"
```

---

#### Autopep8

```
autopep8>=2.0.0
```

**Python code formatter** - Alternative to black

**More conservative:**
- Fixes only PEP 8 violations
- Less opinionated than black
- Preserves more original formatting

**Usage:**
```python
import autopep8

def format_with_autopep8(code: str) -> str:
    return autopep8.fix_code(code, options={'aggressive': 1})
```

**Project strategy:** Try black first, fallback to autopep8

---

## 📁 File: `server/start_server.sh`

### Mục đích
**Local development script** - Không dùng trên Render

### Nội dung

```bash
#!/bin/bash
# Script khởi động FastAPI server trên Ubuntu (kết nối Ollama qua Tailscale)

cd "$(dirname "$0")"

# Optional: activate a virtualenv if present at ./venv or the user's venv path
if [ -f "./venv/bin/activate" ]; then
    source ./venv/bin/activate
elif [ -f "/home/sagito/venv/bin/activate" ]; then
    source /home/sagito/venv/bin/activate
fi

# Use environment PORT if provided (Replit sets $PORT)
PORT=${PORT:-9000}
HOST=${HOST:-0.0.0.0}

echo "🚀 Starting FastAPI server on ${HOST}:${PORT}..."
echo "📡 Ollama endpoint: ${OLLAMA_URL:-http://127.0.0.1:11434}"

# Production-ready invocation (no --reload). For local dev you can add --reload.
uvicorn app.main:app --host ${HOST} --port ${PORT}
```

---

### Phân tích Script

#### Shebang

```bash
#!/bin/bash
```

**Specify interpreter** - Bash shell

---

#### Change Directory

```bash
cd "$(dirname "$0")"
```

**Navigate to script's directory**

**Breakdown:**
- `$0` - Script path (`/home/sagito/Desktop/BTL_Python/server/start_server.sh`)
- `dirname "$0"` - Extract directory (`/home/sagito/Desktop/BTL_Python/server`)
- `cd ...` - Change to that directory

**Why?** Relative paths work correctly (e.g., `./venv/bin/activate`)

---

#### Virtualenv Activation

```bash
if [ -f "./venv/bin/activate" ]; then
    source ./venv/bin/activate
elif [ -f "/home/sagito/venv/bin/activate" ]; then
    source /home/sagito/venv/bin/activate
fi
```

**Try two locations:**

**1. Local venv** (`./venv/`)
```bash
cd /home/sagito/Desktop/BTL_Python/server
python3 -m venv venv
source venv/bin/activate
```

**2. User venv** (`/home/sagito/venv/`)
```bash
# Global venv for all projects
python3 -m venv /home/sagito/venv
```

**Benefits:**
- Isolated dependencies
- Prevent conflicts
- Clean system Python

---

#### Port Configuration

```bash
PORT=${PORT:-9000}
HOST=${HOST:-0.0.0.0}
```

**Bash parameter expansion:** `${VAR:-default}`

**Logic:**
```bash
# If PORT is set:
PORT=8080 ./start_server.sh  # Uses 8080

# If PORT is not set:
./start_server.sh  # Uses 9000 (default)
```

**Why 9000?**
- Unprivileged port (>1024)
- Not commonly used (avoid conflicts)
- Easy to remember

**Why 0.0.0.0?**
- Bind to all network interfaces
- Accept connections from:
  - `localhost` (127.0.0.1)
  - LAN (192.168.x.x)
  - Internet (if firewall allows)

---

#### Status Messages

```bash
echo "🚀 Starting FastAPI server on ${HOST}:${PORT}..."
echo "📡 Ollama endpoint: ${OLLAMA_URL:-http://127.0.0.1:11434}"
```

**User feedback** với emojis!

**Example output:**
```
🚀 Starting FastAPI server on 0.0.0.0:9000...
📡 Ollama endpoint: http://127.0.0.1:11434
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:9000 (Press CTRL+C to quit)
```

---

#### Start Uvicorn

```bash
uvicorn app.main:app --host ${HOST} --port ${PORT}
```

**Production mode:**
- No `--reload` (stability)
- No `--debug` (security)
- Simple command

**For development, add:**
```bash
uvicorn app.main:app --host ${HOST} --port ${PORT} --reload
```

---

## 📁 File: `server/.env.example`

### Mục đích
**Environment template** - Copy to `.env` for local dev

### Nội dung chi tiết

```bash
# Cấu hình cho server - Copy file này thành .env và điền giá trị thực

# ===== GROQ CLOUD CONFIGURATION =====
# Get your API key from: https://console.groq.com/keys
# Groq provides free, fast inference - no local setup required!
GROQ_API_KEY=gsk_your_api_key_here

# Recommended models:
# - llama-3.1-70b-versatile (fast, general purpose, default)
# - codellama-34b-instruct (code-specific)
# - mixtral-8x7b-32768 (large context window)
GROQ_MODEL=llama-3.1-70b-versatile

# ===== SERVER CONFIGURATION =====
# Host và Port (mặc định: 0.0.0.0:9000)
# Render/Replit tự động set PORT, không cần đổi
HOST=0.0.0.0
PORT=9000

# API Key nội bộ của server này (để bảo vệ endpoints)
API_KEY=5conmeo

# ===== LLM SETTINGS =====
# Context window size (số token tối đa)
NUM_CTX=4096

# Timeout cho request tới Groq API (giây)
TIMEOUT_SECONDS=30

# ===== FEATURES =====
# Bật postprocessing để loại bỏ markdown và format code
POSTPROCESS_ENABLED=true

# ===== CORS =====
# Domains được phép gọi API (mặc định: *)
ALLOW_ORIGINS=*
```

---

### Phân tích Environment Variables

#### Groq Configuration

**GROQ_API_KEY:**
```bash
GROQ_API_KEY=gsk_your_api_key_here
```

**How to get:**
1. Visit https://console.groq.com/keys
2. Sign up (free!)
3. Create API key
4. Copy vào `.env`

**Free tier:**
- 30 requests/minute
- 1000 requests/day
- No credit card required

---

**GROQ_MODEL:**
```bash
GROQ_MODEL=llama-3.1-70b-versatile
```

**Available models:**

| Model | Size | Best For | Speed |
|-------|------|----------|-------|
| llama-3.1-70b-versatile | 70B | General, balanced | Fast |
| codellama-34b-instruct | 34B | Code generation | Medium |
| mixtral-8x7b-32768 | 8x7B | Long context | Fast |
| qwen2.5-coder:7b | 7B | Code (specialized) | Very fast |

---

#### Server Configuration

**HOST:**
```bash
HOST=0.0.0.0
```

**Bind addresses:**
- `0.0.0.0` - All interfaces (default) ✅
- `127.0.0.1` - Localhost only (secure, local-only)
- `192.168.1.100` - Specific interface

---

**PORT:**
```bash
PORT=9000
```

**Port selection:**
- `80` - HTTP (requires root)
- `443` - HTTPS (requires root)
- `8000` - Common dev port (Django, Flask)
- `8080` - Common alt HTTP
- `9000` - Our choice! ✅

**Render overrides:** `$PORT` environment variable

---

**API_KEY:**
```bash
API_KEY=5conmeo
```

**Weak password!** Production nên dùng:
```bash
# Generate strong key:
API_KEY=$(openssl rand -hex 32)
# e.g., API_KEY=a7b3f9d8e2c4f6a1b5d7e9f3c8a6b4d2e7f9a3c5d8e2f6b4a9c7d5e3f1a8b6c4
```

---

#### LLM Settings

**NUM_CTX:**
```bash
NUM_CTX=4096
```

**Context window sizes:**
- 2048 - Small, fast
- 4096 - Balanced ✅
- 8192 - Large context
- 32768 - Mixtral only (huge!)

---

**TIMEOUT_SECONDS:**
```bash
TIMEOUT_SECONDS=30
```

**Groq API timeout:**
- 10s - Too short (might fail)
- 30s - Good balance ✅
- 60s - Very patient (slow UX)

---

#### Features

**POSTPROCESS_ENABLED:**
```bash
POSTPROCESS_ENABLED=true
```

**Values:**
- `true` - Enable postprocessing ✅
- `false` - Raw LLM output
- `1` - Also treated as true
- `0` - Also treated as false

---

#### CORS

**ALLOW_ORIGINS:**
```bash
ALLOW_ORIGINS=*
```

**Options:**
```bash
# Allow all (current):
ALLOW_ORIGINS=*

# Specific domain:
ALLOW_ORIGINS=https://myapp.com

# Multiple domains:
ALLOW_ORIGINS=https://myapp.com,https://app.example.com

# VS Code extension:
ALLOW_ORIGINS=vscode-webview://*
```

---

## 🚀 Quy trình Deploy lên Render

### Step-by-Step Guide

#### 1. Chuẩn bị Code

```bash
# Ensure files exist:
✅ server/render.yaml
✅ server/requirements.txt
✅ server/Procfile (backup)
✅ server/app/main.py
✅ .git/ (Git repository)
```

---

#### 2. Push to GitHub

```bash
# Initialize git (if not already):
git init
git add .
git commit -m "Initial commit"

# Add remote:
git remote add origin https://github.com/Sagitoaz/BTL_Python.git

# Push:
git push -u origin main
```

---

#### 3. Connect Render to GitHub

**Web UI:**
1. Visit https://render.com
2. Sign up/Login (with GitHub)
3. Click "New +" → "Web Service"
4. Connect GitHub repository
5. Select `BTL_Python` repo
6. Grant access

---

#### 4. Configure Service

**Settings:**

**Name:** `btl-python-server`

**Branch:** `main` (or `dev`)

**Root Directory:** `server/` ⚠️ **IMPORTANT!**
- Render needs to `cd server/` first
- Otherwise can't find `requirements.txt`

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Plan:** Free (512MB RAM, shared CPU)

---

#### 5. Environment Variables

**Add trong Render Dashboard:**

```
GROQ_API_KEY = gsk_xxxxxxxxxxxxxxxxxxxx
GROQ_MODEL = qwen2.5-coder:7b
API_KEY = 5conmeo
NUM_CTX = 4096
POSTPROCESS_ENABLED = true
ALLOW_ORIGINS = *
```

**How to add:**
1. Go to service → Environment
2. Click "Add Environment Variable"
3. Enter key-value pairs
4. Save changes

---

#### 6. Deploy!

**Automatic deployment:**
```
Push to GitHub → Render detects change → Auto-deploy
```

**Manual deployment:**
1. Go to service dashboard
2. Click "Manual Deploy" → "Deploy latest commit"

**Build process:**
```
==> Cloning from https://github.com/Sagitoaz/BTL_Python...
==> Checking out commit abc123def in branch main
==> Running build command 'pip install -r requirements.txt'...
    Collecting fastapi>=0.104.1
    Downloading fastapi-0.104.1-py3-none-any.whl (92 kB)
    ...
    Successfully installed fastapi-0.104.1 uvicorn-0.24.0 ...
==> Build successful! 🎉
==> Starting service with 'uvicorn app.main:app --host 0.0.0.0 --port $PORT'...
    INFO:     Started server process [1]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    INFO:     Uvicorn running on http://0.0.0.0:10000
==> Your service is live at https://btl-python-r9kz.onrender.com 🚀
```

---

#### 7. Verify Deployment

**Health check:**
```bash
curl https://btl-python-r9kz.onrender.com/health
```

**Expected response:**
```json
{
  "status": "ok",
  "version": "1.3.1",
  "model": "qwen2.5-coder:7b",
  "timestamp": "2025-11-11T12:34:56.789Z"
}
```

**Test completion:**
```bash
curl -X POST https://btl-python-r9kz.onrender.com/complete \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 5conmeo" \
  -d '{
    "language": "python",
    "prefix": "def add(a, b):\n    ",
    "suffix": "",
    "max_tokens": 50
  }'
```

**Expected:**
```json
{
  "completion": "return a + b",
  "model": "qwen2.5-coder:7b",
  "completion_id": "abc-123-xyz"
}
```

---

## 🔄 CI/CD Pipeline

### Automatic Deployment Flow

```
Developer pushes code to GitHub
            ↓
GitHub webhook triggers Render
            ↓
Render clones repository
            ↓
Render runs buildCommand (pip install)
            ↓
Build success? ──NO──> Rollback to previous version
      │
     YES
      ↓
Render runs startCommand (uvicorn)
      ↓
Health check pass? ──NO──> Alert + rollback
      │
     YES
      ↓
Traffic switched to new version
      ↓
Old version shut down
      ↓
Deployment complete! 🎉
```

---

### Rollback Strategy

**Automatic rollback if:**
- Build fails (pip install error)
- Start fails (Python import error)
- Health check fails (timeout, 500 error)

**Manual rollback:**
1. Go to Render dashboard
2. Events → Find previous successful deploy
3. Click "Rollback to this version"
4. Confirm

**Zero downtime:** Old version runs until new version healthy

---

## 📊 Monitoring & Logs

### Render Dashboard Features

#### 1. Logs Tab

**Real-time logs:**
```
2025-11-11 12:34:56 INFO:     Started server process [1]
2025-11-11 12:34:56 INFO:     Waiting for application startup.
2025-11-11 12:34:56 INFO:     Application startup complete.
2025-11-11 12:35:10 INFO:     POST /complete - 200 OK (1.23s)
2025-11-11 12:35:15 ERROR:    POST /complete - 500 Internal Server Error
```

**Log filters:**
- INFO - Normal operations
- WARNING - Non-critical issues
- ERROR - Failures (need attention!)
- DEBUG - Detailed traces (if enabled)

---

#### 2. Metrics Tab

**Graphs:**
- **CPU usage** (%) over time
- **Memory usage** (MB) over time
- **Request rate** (req/s)
- **Response time** (ms) p50, p95, p99

**Free tier limits:**
- 512MB RAM (exceed = crash!)
- Shared CPU (no guarantees)
- 750 hours/month (31.25 days, always-on OK)

---

#### 3. Events Tab

**Deployment history:**
```
2025-11-11 12:30:00  Deploy started (commit abc123)
2025-11-11 12:31:00  Build successful
2025-11-11 12:31:30  Deploy live
2025-11-10 08:00:00  Deploy started (commit def456)
2025-11-10 08:00:45  Build failed (rollback)
```

---

#### 4. Environment Tab

**Edit environment variables:**
- Add new variables
- Update values
- Delete variables

**Changes trigger redeploy!**

---

### External Monitoring

**UptimeRobot (free):**
```
Monitor: https://btl-python-r9kz.onrender.com/health
Interval: 5 minutes
Alert: Email if down
```

**Logs aggregation:**
- Logtail
- Papertrail
- Datadog (paid)

---

## 🔐 Security Best Practices

### 1. Strong API Keys

**Bad:**
```bash
API_KEY=5conmeo  # Easy to guess!
```

**Good:**
```bash
API_KEY=$(openssl rand -hex 32)
# 64 character random hex
```

---

### 2. HTTPS Only

**Render provides:**
- ✅ Free SSL certificate (Let's Encrypt)
- ✅ Auto-renewal
- ✅ HTTPS by default

**Enforce HTTPS in code:**
```python
# server/app/middleware/https.py
from fastapi import Request, HTTPException

async def https_only(request: Request, call_next):
    if request.url.scheme != "https" and not request.url.hostname == "localhost":
        raise HTTPException(status_code=403, detail="HTTPS required")
    return await call_next(request)
```

---

### 3. Rate Limiting

**Prevent abuse:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/complete")
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def complete_endpoint():
    ...
```

---

### 4. Input Validation

**Pydantic schemas:**
```python
from pydantic import BaseModel, Field

class CompleteRequest(BaseModel):
    prefix: str = Field(..., max_length=10000)  # Prevent huge inputs
    suffix: str = Field(..., max_length=10000)
    max_tokens: int = Field(default=300, ge=1, le=2000)  # Clamp
```

---

### 5. Secrets Management

**Never commit:**
```bash
# .gitignore
.env
.env.local
.env.production
*.pem
*.key
```

**Use Render environment variables** (encrypted at rest)

---

## 💰 Cost Analysis

### Free Tier Limits

**Render.com Free:**
- ✅ 512MB RAM
- ✅ Shared CPU
- ✅ 750 hours/month (enough for 24/7)
- ✅ Free SSL
- ✅ Auto-deploy
- ❌ Spins down after 15min inactivity (cold start ~30s)

**Groq Free:**
- ✅ 30 requests/minute
- ✅ 1000 requests/day
- ✅ No credit card
- ❌ No guaranteed uptime

---

### Paid Upgrade Options

**Render.com Starter ($7/month):**
- 512MB RAM (same)
- Dedicated CPU (faster!)
- No spin-down (always hot!)
- Background workers
- Priority support

**Groq Pay-as-you-go:**
- 60 requests/minute (2x)
- Unlimited daily
- $0.10 per 1M tokens (cheap!)
- 99.9% uptime SLA

---

### Alternative Platforms

**Railway ($5/month):**
- Similar to Render
- Better free tier (500 hours)
- Nicer UI

**Fly.io (Free tier):**
- 3 shared VMs
- Global edge deployment
- More complex setup

**Heroku (No free tier):**
- Eco Dyno: $5/month
- Reliable, mature
- Great documentation

**Vercel (Free tier):**
- Serverless functions
- Global CDN
- Limited to 10s timeout (not ideal for LLM)

---

## 🧪 Test Cases

### Test 1: Health Check

**Request:**
```bash
curl https://btl-python-r9kz.onrender.com/health
```

**Expected:**
```json
{
  "status": "ok",
  "version": "1.3.1",
  "model": "qwen2.5-coder:7b"
}
```

**Status code:** 200 OK

---

### Test 2: Unauthorized Access

**Request (no API key):**
```bash
curl -X POST https://btl-python-r9kz.onrender.com/complete \
  -H "Content-Type: application/json" \
  -d '{"language":"python","prefix":"def add","suffix":""}'
```

**Expected:**
```json
{
  "detail": "Not authenticated"
}
```

**Status code:** 401 Unauthorized

---

### Test 3: Valid Completion

**Request:**
```bash
curl -X POST https://btl-python-r9kz.onrender.com/complete \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 5conmeo" \
  -d '{
    "language": "python",
    "prefix": "def factorial(n):\n    ",
    "suffix": "",
    "max_tokens": 100
  }'
```

**Expected:**
```json
{
  "completion": "if n <= 1:\n        return 1\n    return n * factorial(n - 1)",
  "model": "qwen2.5-coder:7b",
  "completion_id": "abc-123-xyz"
}
```

**Status code:** 200 OK

---

### Test 4: Streaming

**Request:**
```bash
curl -X POST https://btl-python-r9kz.onrender.com/complete-stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 5conmeo" \
  -d '{
    "language": "python",
    "prefix": "# Calculate sum\n",
    "suffix": ""
  }'
```

**Expected (SSE stream):**
```
data: {"completion":"def"}
data: {"completion":" sum"}
data: {"completion":"_numbers"}
data: {"completion":"(arr"}
data: {"completion":"):\n"}
data: {"completion":"    return"}
data: {"completion":" sum"}
data: {"completion":"(arr"}
data: {"completion":")\n"}
data: [DONE]
```

**Status code:** 200 OK

---

### Test 5: Cold Start

**Scenario:** Service spun down (15min inactive)

**Request:**
```bash
time curl https://btl-python-r9kz.onrender.com/health
```

**First request (cold start):**
```
{"status":"ok","version":"1.3.1"}

real    0m35.123s  ← ~35 seconds!
user    0m0.012s
sys     0m0.008s
```

**Second request (warm):**
```
{"status":"ok","version":"1.3.1"}

real    0m0.456s  ← Fast! ✅
user    0m0.010s
sys     0m0.006s
```

---

### Test 6: Load Test

**ApacheBench:**
```bash
ab -n 100 -c 10 \
  -H "Authorization: Bearer 5conmeo" \
  -p complete.json \
  -T application/json \
  https://btl-python-r9kz.onrender.com/complete
```

**Expected results:**
```
Concurrency Level:      10
Time taken for tests:   45.123 seconds
Complete requests:      100
Failed requests:        0
Requests per second:    2.22 [#/sec] (mean)
Time per request:       4512.3 [ms] (mean)
```

**Free tier performance:** ~2-5 req/s

---

## 📈 Performance Optimization

### 1. Enable Caching

**Redis cache (requires paid plan):**
```python
import redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

redis_client = redis.from_url("redis://...")
FastAPICache.init(RedisBackend(redis_client), prefix="btl-cache")

@app.post("/complete")
@cache(expire=300)  # Cache 5 minutes
async def complete_endpoint():
    ...
```

---

### 2. Connection Pooling

**Already implemented via httpx:**
```python
# server/app/core/http.py
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    )
)
```

---

### 3. Reduce Cold Starts

**Render-specific:**
```yaml
# render.yaml
services:
  - type: web
    healthCheckPath: /health
    autoDeploy: true
```

**External keep-alive (cron job):**
```bash
# Ping every 10 minutes
*/10 * * * * curl -s https://btl-python-r9kz.onrender.com/health > /dev/null
```

---

### 4. Optimize Dependencies

**Remove unused packages:**
```bash
# Before:
pip list | wc -l
# 50 packages

# After (only essentials):
# 15 packages

# Faster build + smaller image
```

---

## 🎯 Key Points cho Thuyết trình

### 1. Zero-Cost Deployment

**Highlight:**
- ✅ Render.com free tier (512MB, 750hr/month)
- ✅ Groq API free tier (30 req/min)
- ✅ No credit card required
- ✅ Production-ready HTTPS

**Total cost:** $0/month! 💰

---

### 2. Infrastructure as Code

**render.yaml benefits:**
- ✅ Version controlled (Git)
- ✅ Reproducible (deploy anywhere)
- ✅ Documented (self-explanatory)
- ✅ Automated (no manual clicks)

**One file = Full deployment config!**

---

### 3. CI/CD Pipeline

**Automatic workflow:**
```
Git push → Webhook → Build → Test → Deploy → Health check
```

**Zero manual steps!** Shipping code = typing `git push`

---

### 4. Environment-based Config

**12-factor app principles:**
- ✅ Config in environment (not code)
- ✅ Different values per env (dev/staging/prod)
- ✅ Secure (secrets not in Git)
- ✅ Flexible (change without redeploy)

---

### 5. Production-Ready Features

**Built-in:**
- ✅ Free SSL (HTTPS)
- ✅ Auto-scaling (within free tier limits)
- ✅ Health checks
- ✅ Automatic rollback
- ✅ Logging & monitoring
- ✅ Custom domains (paid)

---

### 6. Developer Experience

**Smooth workflow:**
1. Edit code locally
2. Test with `start_server.sh`
3. Commit & push
4. Auto-deploy (30-60s)
5. Verify via health check

**No DevOps expertise required!**

---

### 7. Scalability Path

**Growth options:**
```
Free tier (0 users)
    ↓ More traffic
Starter $7/mo (100s of users)
    ↓ More traffic
Pro $25/mo (1000s of users)
    ↓ More traffic
Custom plan / Self-hosted Kubernetes
```

**Start free, scale when needed!**

---

## 🔍 Common Issues & Solutions

### Issue 1: Build Fails

**Error:**
```
ERROR: Could not find a version that satisfies the requirement fastapi>=0.104.1
```

**Solution:**
```bash
# Check Python version:
python --version  # Should be 3.11+

# Update requirements.txt:
fastapi>=0.100.0  # Lower version requirement
```

---

### Issue 2: Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'app'
```

**Solution:**
```yaml
# render.yaml - Set correct root directory:
rootDirectory: server/  # ← IMPORTANT!
```

---

### Issue 3: Port Binding

**Error:**
```
[Errno 98] Address already in use
```

**Solution:**
```bash
# Must use $PORT on Render:
uvicorn app.main:app --host 0.0.0.0 --port $PORT  # ✅ Correct

# Not:
uvicorn app.main:app --host 0.0.0.0 --port 9000   # ❌ Wrong
```

---

### Issue 4: CORS Errors

**Error:**
```
Access to fetch at '...' has been blocked by CORS policy
```

**Solution:**
```python
# server/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific origins
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### Issue 5: Timeout

**Error:**
```
TimeoutError: Request to Groq API timed out
```

**Solution:**
```python
# Increase timeout:
async with httpx.AsyncClient(timeout=60.0) as client:
    ...
```

---

### Issue 6: Memory Limit

**Error:**
```
Out of memory. Upgrade to a larger plan.
```

**Solution:**
- Optimize code (reduce memory usage)
- Upgrade to Starter plan ($7/mo, more RAM)
- Use streaming (less memory)

---

## 🚀 Summary

**Deployment setup của BTL AI Coder:**

### Files
1. ✅ **render.yaml** - Infrastructure as Code (main config)
2. ✅ **Procfile** - Heroku-style backup
3. ✅ **requirements.txt** - Python dependencies
4. ✅ **start_server.sh** - Local development
5. ✅ **.env.example** - Environment template

### Key Technologies
- **Render.com** - PaaS hosting (free tier)
- **Uvicorn** - ASGI production server
- **Groq API** - Fast LLM inference
- **FastAPI** - Modern Python web framework

### Deployment Flow
```
Code → Git → GitHub → Webhook → Render → Build → Deploy → Live!
```

### Benefits
- 🆓 **Zero cost** (free tiers)
- 🚀 **Fast deployment** (30-60s)
- 🔒 **Secure** (HTTPS, env secrets)
- 📊 **Monitored** (logs, metrics)
- ♻️ **Automated** (CI/CD)
- 📈 **Scalable** (upgrade path)

**Perfect cho BTL projects và thuyết trình!** 🎓✨
