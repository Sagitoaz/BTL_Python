# 🚀 Deploy to Render with Groq Cloud

## Why Groq?
- ✅ **Free & Fast**: No local server needed, lightning-fast inference
- ✅ **24/7 Availability**: Always-on, no cold starts after setup
- ✅ **Easy Setup**: Just need API key, no complex infrastructure
- ✅ **Better than Ollama**: No local GPU, no ngrok tunnels, no Cloudflare setup

## Prerequisites
1. GitHub account with your repo
2. Render account (free tier works!)
3. Groq account (free at https://console.groq.com)

## Step 1: Get Groq API Key
1. Go to https://console.groq.com
2. Sign up (it's free!)
3. Navigate to **API Keys**
4. Click **Create API Key**
5. Copy the key (starts with `gsk_...`)

## Step 2: Deploy to Render
1. Push your code to GitHub
2. Go to https://dashboard.render.com
3. Click **New** → **Web Service**
4. Connect your GitHub repo
5. Configure:
   - **Name**: `btl-python-server`
   - **Environment**: `Python 3`
   - **Build Command**: `cd server && pip install -r requirements.txt`
   - **Start Command**: `cd server && bash start_server.sh`
   - **Plan**: Free

## Step 3: Set Environment Variables
In Render dashboard, add these environment variables:

```bash
GROQ_API_KEY=gsk_your_actual_key_here
GROQ_MODEL=llama-3.1-70b-versatile
API_KEY=5conmeo
NUM_CTX=4096
POSTPROCESS_ENABLED=true
```

**IMPORTANT**: Replace `gsk_your_actual_key_here` with your real Groq API key!

## Step 4: Deploy
1. Click **Create Web Service**
2. Wait 2-3 minutes for deployment
3. Your server URL will be: `https://your-service-name.onrender.com`

## Step 5: Test
```bash
# Test health endpoint
curl https://your-service-name.onrender.com/health

# Should return:
# {"status":"ok","model":"llama-3.1-70b-versatile","available_models":[...]}

# Test completion
curl -X POST https://your-service-name.onrender.com/complete \
  -H "Authorization: Bearer 5conmeo" \
  -H "Content-Type: application/json" \
  -d '{
    "prefix": "def fibonacci(n):\n    ",
    "suffix": "",
    "language": "python",
    "max_tokens": 100
  }'
```

## Step 6: Update VSCode Extension
Update `.vscode/settings.json`:

```json
{
  "btl.serverUrl": "https://your-service-name.onrender.com",
  "btl.apiKey": "5conmeo",
  "btl.timeoutMs": 15000
}
```

## Troubleshooting

### Health returns "degraded"
- Check GROQ_API_KEY is set correctly in Render environment variables
- Verify key is valid at https://console.groq.com/keys
- Check logs: `https://dashboard.render.com/web/{your-service}/logs`

### No completions
- Ensure API_KEY matches between server and VSCode extension
- Check extension output logs in VSCode
- Verify Render logs for errors

### Slow responses
- First request after idle may take 30-60s (Render cold start)
- Subsequent requests should be <2s with Groq
- Consider upgrading to Render paid plan to avoid cold starts

## Available Groq Models
- `llama-3.1-70b-versatile` (default) - Fast, balanced
- `codellama-34b-instruct` - Code-specific
- `mixtral-8x7b-32768` - Large context window
- `gemma-7b-it` - Lightweight

Change model by updating `GROQ_MODEL` environment variable in Render.

## Cost
- **Groq Free Tier**: 30 requests/minute, 6000 tokens/minute
- **Render Free Tier**: 750 hours/month (enough for always-on)
- **Total**: $0/month! 🎉

## Next Steps
1. Test completions in VSCode
2. Monitor usage at https://console.groq.com/dashboard
3. Upgrade Groq/Render plans if needed for higher traffic
4. Implement telemetry (Phase 2) to collect user data
