# 🛠️ HƯỚNG DẪN SETUP MÔI TRƯỜNG PHÁT TRIỂN

> **Dành cho:** Nhóm BTL_Python - 4 developers  
> **Thời gian setup:** ~30 phút  
> **Hệ điều hành:** Windows (primary), macOS/Linux (secondary)

---

## 📋 YÊU CẦU HỆ THỐNG

### **Minimum Requirements**
- **OS:** Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **RAM:** 8GB (khuyến nghị 16GB)
- **Storage:** 5GB free space
- **Network:** Stable internet connection

### **Required Software**
- **Python:** 3.11+ (khuyến nghị 3.11.5)
- **Node.js:** 18+ (khuyến nghị 20.x LTS)
- **VS Code:** Latest version
- **Git:** Latest version
- **Ollama:** Latest version (cho local testing)

---

## 🐍 PYTHON ENVIRONMENT SETUP

### **Bước 1: Cài đặt Python**

#### Windows (PowerShell as Administrator):
```powershell
# Option 1: Via Microsoft Store (khuyến nghị)
# Tìm "Python 3.11" trong Microsoft Store và cài đặt

# Option 2: Via Chocolatey
choco install python311 -y

# Option 3: Download từ python.org
# https://www.python.org/downloads/windows/
```

#### macOS:
```bash
# Via Homebrew
brew install python@3.11
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

### **Bước 2: Tạo Virtual Environment**

```powershell
# Windows PowerShell
cd "c:\Users\Sagito\OneDrive\Desktop\BTL Python\BTL_Python"
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux/macOS
cd /path/to/BTL_Python
python3.11 -m venv .venv
source .venv/bin/activate
```

### **Bước 3: Cài đặt Python Dependencies**

```powershell
# Server dependencies
cd server
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Tools dependencies  
cd ..
pip install requests httpx pytest
```

### **Bước 4: Kiểm tra Python Setup**

```powershell
# Kiểm tra Python version
python --version
# Expected: Python 3.11.x

# Test server
cd server
python -m pytest tests/ -v
# Expected: 3 tests passed

# Test CLI tools
cd ..
echo "def test():" | python tools/cli.py --help
```

---

## 📦 NODE.JS & TYPESCRIPT SETUP

### **Bước 1: Cài đặt Node.js**

#### Windows:
```powershell
# Via Chocolatey
choco install nodejs -y

# Hoặc download từ https://nodejs.org/
```

#### macOS:
```bash
# Via Homebrew
brew install node
```

#### Linux:
```bash
# Via NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### **Bước 2: Cài đặt Dependencies**

```powershell
# Trong project root
npm install

# Kiểm tra installation
npm list
```

### **Bước 3: Compile TypeScript**

```powershell
# Compile một lần
npm run compile

# Watch mode (auto-recompile khi save)
npm run watch
```

### **Bước 4: Kiểm tra Node.js Setup**

```powershell
# Check versions
node --version    # Should be v18+ or v20+
npm --version     # Should be 8+ or 10+

# Test compilation
ls out/           # Should see .js files
```

---

## 🎯 VS CODE SETUP

### **Bước 1: Cài đặt VS Code**

Download và cài đặt từ: https://code.visualstudio.com/

### **Bước 2: Required Extensions**

Cài đặt các extensions sau trong VS Code:

```json
// .vscode/extensions.json (đã có trong project)
{
  "recommendations": [
    "ms-python.python",
    "ms-python.pylint", 
    "ms-python.black-formatter",
    "ms-vscode.vscode-typescript-next",
    "bradlc.vscode-tailwindcss"
  ]
}
```

### **Bước 3: Workspace Settings**

VS Code sẽ tự động load settings từ `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./.venv/Scripts/python.exe",
  "python.terminal.activateEnvironment": true,
  "typescript.preferences.moduleResolution": "node"
}
```

### **Bước 4: Test Extension Development**

```powershell
# Mở project trong VS Code
code .

# Press F5 để run extension trong Development Host
# Hoặc Ctrl+Shift+P > "Tasks: Run Task" > "npm: watch"
```

---

## 🤖 OLLAMA SETUP (Cho Local Testing)

### **Bước 1: Cài đặt Ollama**

#### Windows:
```powershell
# Download và cài đặt từ https://ollama.ai/
# Hoặc via PowerShell
Invoke-WebRequest -Uri "https://ollama.ai/install.ps1" -OutFile "install.ps1"
.\install.ps1
```

#### macOS:
```bash
# Via Homebrew
brew install ollama
```

#### Linux:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### **Bước 2: Pull Model**

```powershell
# Start Ollama service
ollama serve

# Trong terminal khác, pull model
ollama pull qwen2.5-coder:7b

# Kiểm tra models available
ollama list
```

### **Bước 3: Test Ollama**

```powershell
# Test model
ollama run qwen2.5-coder:7b "def fibonacci(n):"

# Test API
curl http://localhost:11434/api/tags
```

---

## 🔧 DEVELOPMENT WORKFLOW

### **Daily Development Setup**

```powershell
# 1. Activate Python environment
.\.venv\Scripts\Activate.ps1

# 2. Start TypeScript watch mode (Terminal 1)
npm run watch

# 3. Start Ollama service (Terminal 2) 
ollama serve

# 4. Start development server (Terminal 3)
cd server
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000

# 5. Open VS Code và press F5 để test extension
code .
```

### **Testing Workflow**

```powershell
# Server tests
cd server && python -m pytest tests/ -v

# Extension testing (trong VS Code Development Host)
# 1. Press F5
# 2. Create test.py file
# 3. Type Python code và xem suggestions

# CLI tools testing
echo "def add(a,b):" | python tools/cli.py --server http://localhost:9000 --api-key 5conmeo

# Stress testing
python tools/stress.py --server http://localhost:9000 --api-key 5conmeo --requests 10
```

---

## 🌐 ENVIRONMENT VARIABLES

### **Development .env File**

Tạo file `.env` trong folder `server/`:

```bash
# server/.env
OLLAMA_URL=http://127.0.0.1:11434
MODEL=qwen2.5-coder:7b
API_KEY=5conmeo
TIMEOUT_SECONDS=120
ALLOW_ORIGINS=*
POSTPROCESS_ENABLED=true
```

### **VS Code User Settings**

Thêm vào VS Code User Settings (`Ctrl+,`):

```json
{
  "btl.serverUrl": "http://localhost:9000",
  "btl.apiKey": "5conmeo", 
  "btl.enableStreaming": true,
  "btl.timeoutMs": 8000
}
```

### **System Environment Variables**

```powershell
# Windows PowerShell (cho session hiện tại)
$env:SERVER_URL="http://localhost:9000"
$env:API_KEY="5conmeo"
$env:BTL_TIMEOUT="20.0"

# Để permanent, thêm vào System Environment Variables
```

---

## 🚦 VERIFICATION CHECKLIST

### **✅ Python Environment**
- [ ] Python 3.11+ installed và trong PATH
- [ ] Virtual environment activated 
- [ ] All dependencies installed (`pip list` shows fastapi, uvicorn, etc.)
- [ ] Server tests pass (`pytest tests/` = 3 passed)

### **✅ Node.js Environment** 
- [ ] Node.js 18+ installed
- [ ] npm dependencies installed
- [ ] TypeScript compiles without errors (`npm run compile`)
- [ ] `out/` folder contains compiled .js files

### **✅ VS Code Environment**
- [ ] VS Code opens project correctly
- [ ] Python interpreter detected (bottom-left status bar)
- [ ] Extensions installed và active
- [ ] F5 launches Extension Development Host

### **✅ Ollama Environment**
- [ ] Ollama service running (`ollama serve`)
- [ ] Model downloaded (`ollama list` shows qwen2.5-coder:7b)
- [ ] API accessible (`curl http://localhost:11434/api/tags`)

### **✅ Integration Test**
- [ ] Server starts successfully (`uvicorn app.main:app`)
- [ ] Health endpoint returns 200 (`curl http://localhost:9000/health`)
- [ ] CLI tools work (`echo "def test():" | python tools/cli.py`)
- [ ] Extension shows suggestions trong VS Code Development Host

---

## 🔧 COMMON ISSUES & FIXES

### **Python Issues**

**Issue:** `python` command not found
```powershell
# Fix: Add Python to PATH hoặc use full path
C:\Users\[USER]\AppData\Local\Programs\Python\Python311\python.exe
```

**Issue:** `pip install` fails with permissions
```powershell
# Fix: Use --user flag hoặc run as Administrator
pip install --user package_name
```

**Issue:** Virtual environment not activating
```powershell
# Fix: Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### **Node.js Issues**

**Issue:** `npm install` fails with network errors
```powershell  
# Fix: Use different registry
npm install --registry https://registry.npmjs.org/
```

**Issue:** TypeScript compilation errors
```powershell
# Fix: Clear cache và reinstall
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### **VS Code Issues**

**Issue:** Extension not loading trong Development Host
- Check Terminal output cho errors
- Ensure TypeScript compiled successfully
- Restart VS Code và try F5 again

**Issue:** Python interpreter not detected
- Press `Ctrl+Shift+P` > "Python: Select Interpreter"
- Choose `.venv/Scripts/python.exe`

### **Ollama Issues**

**Issue:** Model download fails
```powershell
# Fix: Try smaller model first
ollama pull qwen2.5-coder:1.5b
```

**Issue:** Ollama service won't start
- Check port 11434 is not in use
- Restart với Administrator privileges
- Check firewall settings

---

## 📞 SUPPORT & RESOURCES

### **Documentation**
- **Project Docs:** `TEST_GUIDE.md`, `TROUBLESHOOTING.md` 
- **VS Code API:** https://code.visualstudio.com/api
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Ollama Docs:** https://ollama.ai/

### **Getting Help**
1. Check `TROUBLESHOOTING.md` first
2. Search existing GitHub Issues
3. Run diagnostic commands:
   ```powershell
   # Full health check
   python tools/test_matrix.py
   .\scripts\quick-test.ps1
   ```
4. Create GitHub Issue với full error logs

### **Team Communication**
- **Daily standups:** 9:00 AM mỗi ngày
- **Code reviews:** All PRs require 1 approval
- **Emergency contact:** Team lead phone/Slack

---

**🎉 Setup complete! Bạn đã sẵn sàng để contribute vào BTL_Python project!**

Next steps: Đọc `MVP_PLAN.md` để biết task cụ thể cho role của bạn.