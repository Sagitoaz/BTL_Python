# 🚀 AI Code Completion - Production Ready

> **GitHub Copilot-like code completion** powered by Groq Cloud (llama-3.3-70b-versatile)  
> Fast, accurate, and FREE! ⚡

---

## ✨ Features

### Core Capabilities
- ✅ **Real-time code completion** for Python, JavaScript, TypeScript, and more
- ✅ **Context-aware suggestions** using prefix/suffix analysis
- ✅ **Zero markdown artifacts** - Clean code output only
- ✅ **Smart indentation** - Respects your code style
- ✅ **Auto-formatting** with black/autopep8
- ✅ **Sub-second latency** (P50: 667ms)
- ✅ **100% success rate** in production tests

### Advanced Features
- 📊 **Telemetry system** - Collects usage data for fine-tuning
- 🧪 **Automated testing** - Integration tests + monitoring dashboard
- 🔐 **API authentication** - Secured with API keys
- 📈 **Production monitoring** - Real-time metrics and health checks
- 🌐 **CORS enabled** - Use from any domain

---

## 🏗️ Architecture

```
┌─────────────────┐
│  VSCode Client  │
│  (Extension)    │
└────────┬────────┘
         │ HTTPS
         ↓
┌─────────────────────────────────┐
│  FastAPI Server (Render.com)    │
│  - Auth middleware              │
│  - Request ID tracking          │
│  - Telemetry collection         │
└────────┬────────────────────────┘
         │
         ↓
┌─────────────────────────────────┐
│  Groq Cloud API                 │
│  Model: llama-3.3-70b-versatile │
│  Free tier: 30 req/min          │
└─────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────┐
│  Postprocessing Pipeline        │
│  - Strip markdown fences        │
│  - Fix indentation              │
│  - Remove duplicates            │
│  - Auto-format code             │
└─────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Deploy Server

**Option A: Use our deployed server**
```
https://btl-python-r9kz.onrender.com
```

**Option B: Deploy your own**

1. Fork this repo
2. Create Render.com account (free)
3. Connect GitHub repo
4. Add environment variables:
   ```bash
   GROQ_API_KEY=gsk_your_key_here  # Get from console.groq.com
   GROQ_MODEL=llama-3.3-70b-versatile
   API_KEY=your_secret_key
   AUTO_FORMAT=true
   ```
5. Deploy! 🎉

### 2. Install VSCode Extension

1. Open `.vscode/settings.json`
2. Update configuration:
   ```json
   {
     "btl.serverUrl": "https://your-server.onrender.com",
     "btl.apiKey": "your_secret_key",
     "btl.timeoutMs": 15000
   }
   ```
3. Reload VSCode
4. Start coding - completions will appear automatically! ✨

---

## 📊 Performance Metrics

From production monitoring (8 test scenarios):

| Metric | Value | Status |
|--------|-------|--------|
| **Success Rate** | 100% (8/8) | ✅ Excellent |
| **Markdown Detection** | 0% | ✅ Fixed |
| **Avg Latency** | 748ms | ✅ Good |
| **P50 Latency** | 667ms | ✅ Good |
| **P95 Latency** | ~1200ms | ⚠️ Acceptable |
| **Min Latency** | 583ms | ✅ Excellent |
| **Max Latency** | 1237ms | ⚠️ Acceptable |

**Completion Quality:**
- Min: 15 chars
- Max: 96 chars
- Average: 40 chars

---

## 🛠️ Development

### Local Setup

```bash
# Clone repo
git clone https://github.com/Sagitoaz/BTL_Python.git
cd BTL_Python/server

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your GROQ_API_KEY

# Run server
uvicorn app.main:app --reload --port 9000
```

### Run Tests

```bash
# Unit tests
pytest server/tests/ -v

# Integration tests
TEST_SERVER_URL=http://localhost:9000 pytest server/tests/test_integration.py -v

# Monitoring dashboard
python3 tools/monitor_dashboard.py http://localhost:9000 your_api_key
```

---

## 📁 Project Structure

```
BTL_Python/
├── server/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py          # Configuration management
│   │   │   ├── postprocess.py     # Code postprocessing
│   │   │   ├── formatter.py       # Auto-formatting (black/autopep8)
│   │   │   └── security.py        # API authentication
│   │   ├── middleware/
│   │   │   ├── request_id.py      # Request tracking
│   │   │   └── telemetry.py       # Usage data collection
│   │   ├── routers/
│   │   │   ├── completions.py     # Main completion endpoint
│   │   │   ├── health.py          # Health checks
│   │   │   └── admin.py           # Telemetry admin
│   │   ├── services/
│   │   │   └── groq.py            # Groq API integration
│   │   └── schemas/
│   │       └── completion.py      # Request/response models
│   ├── tests/
│   │   ├── test_integration.py    # End-to-end tests
│   │   └── test_postprocess.py    # Unit tests
│   └── requirements.txt
├── src/
│   ├── extension.ts               # VSCode extension entry
│   └── inlineProvider.ts          # Completion provider
├── tools/
│   ├── monitor_dashboard.py       # Monitoring tool
│   ├── test_indent_fix.py         # Indentation tests
│   └── prompt_eval.py             # Prompt evaluation
└── .vscode/
    └── settings.json              # Extension config
```

---

## 🔧 Configuration

### Server Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GROQ_API_KEY` | Groq API key from console.groq.com | - | ✅ |
| `GROQ_MODEL` | Groq model name | `llama-3.3-70b-versatile` | ✅ |
| `API_KEY` | Server API key for authentication | `5conmeo` | ✅ |
| `AUTO_FORMAT` | Enable auto-formatting | `true` | ❌ |
| `POSTPROCESS_ENABLED` | Enable postprocessing | `true` | ❌ |
| `NUM_CTX` | Context window size | `4096` | ❌ |
| `TIMEOUT_SECONDS` | API timeout | `120` | ❌ |

### VSCode Extension Settings

| Setting | Description | Example |
|---------|-------------|---------|
| `btl.serverUrl` | Backend server URL | `https://btl-python-r9kz.onrender.com` |
| `btl.apiKey` | API key for authentication | `5conmeo` |
| `btl.timeoutMs` | Request timeout | `15000` |

---

## 📊 Telemetry & Dataset Collection

### View Statistics

```bash
curl -H "Authorization: Bearer your_api_key" \
  https://your-server.onrender.com/admin/telemetry/stats
```

**Response:**
```json
{
  "total_completions": 1523,
  "languages": {
    "python": 1204,
    "javascript": 319
  },
  "avg_latency_ms": 742.5,
  "data_files": 7
}
```

### Export Training Data

```bash
# Export as JSONL
curl -X POST \
  -H "Authorization: Bearer your_api_key" \
  "https://your-server.onrender.com/admin/telemetry/export?format=jsonl"

# Export as CSV
curl -X POST \
  -H "Authorization: Bearer your_api_key" \
  "https://your-server.onrender.com/admin/telemetry/export?format=csv"
```

### Data Format

Telemetry records include:
- **Request context**: prefix, suffix, language
- **Model output**: completion, latency
- **Metadata**: timestamp, user_id (anonymized), model version
- **Metrics**: completion length, number of lines

Use this data to:
1. Fine-tune models on your team's coding style
2. Analyze common completion patterns
3. Improve prompt engineering
4. A/B test different models

---

## 🧪 Testing & Monitoring

### Integration Tests

```bash
# Run all integration tests
pytest server/tests/test_integration.py -v

# Test specific scenarios
pytest server/tests/test_integration.py::TestCompletionEndpoint::test_basic_completion -v
```

### Monitoring Dashboard

```bash
python3 tools/monitor_dashboard.py https://your-server.onrender.com your_api_key
```

**Output:**
```
🧪 RUNNING TEST SUITE: 8 cases
============================================================
Test 1/8: Simple function
  ✅ 751ms | ✅ | 16 chars
Test 2/8: Fibonacci
  ✅ 668ms | ✅ | 52 chars
...

📊 MONITORING SUMMARY
============================================================
Total Requests: 8
✅ Successful: 8 (100.0%)
❌ Failed: 0 (0.0%)

⏱️  LATENCY STATS:
  Min: 583ms
  Avg: 748ms
  P50: 667ms
  P95: 1200ms
```

---

## 🐛 Troubleshooting

### Server returns "degraded" status

**Cause**: Groq API key not set or invalid

**Fix**:
1. Verify `GROQ_API_KEY` in Render environment variables
2. Check key is valid at https://console.groq.com/keys
3. Ensure no typos in key (starts with `gsk_`)

### Completions have extra indentation

**Cause**: Postprocessing disabled or old code version

**Fix**:
1. Ensure `POSTPROCESS_ENABLED=true` in environment
2. Update to latest code: `git pull origin dev`
3. Redeploy server

### High latency (>2s)

**Cause**: Render cold start or Groq API slowdown

**Fix**:
1. First request after idle always slow (~30-60s) - Render limitation
2. Subsequent requests should be fast (<1s)
3. Consider upgrading to Render paid plan to avoid cold starts
4. Switch to faster model: `GROQ_MODEL=llama-3.1-8b-instant`

### Formatter not working

**Cause**: black/autopep8 not installed

**Fix**:
1. Verify requirements.txt includes `black` and `autopep8`
2. Rebuild on Render: `Settings → Manual Deploy → Deploy`
3. Or disable formatting: `AUTO_FORMAT=false`

---

## 🚧 Roadmap

### Phase 1: Core Features ✅
- [x] Enhanced postprocessing
- [x] Groq Cloud integration
- [x] Markdown removal
- [x] Indentation fixes

### Phase 2: Quality Improvements ✅
- [x] Testing infrastructure
- [x] Monitoring dashboard
- [x] Metrics collection

### Phase 3: Advanced Features ✅
- [x] Code formatter integration
- [x] Telemetry system
- [x] Dataset collection

### Phase 4: Future Enhancements 🚧
- [ ] Multi-line completion improvements
- [ ] Context-aware suggestions with AST parsing
- [ ] Model fine-tuning on collected data
- [ ] Support for more languages (Go, Rust, etc.)
- [ ] Streaming completions in VSCode
- [ ] Caching layer for common patterns

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 🙏 Acknowledgments

- **Groq** for providing fast, free LLM inference
- **Render** for reliable hosting
- **FastAPI** for excellent API framework
- **Black** and **autopep8** for code formatting

---

## 📞 Support

- **Issues**: https://github.com/Sagitoaz/BTL_Python/issues
- **Email**: sagito@example.com
- **Server Status**: https://btl-python-r9kz.onrender.com/health

---

Made with ❤️ by Sagito Team
