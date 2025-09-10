cd C:\code\python_assignment\BTL_Python
New-Item -ItemType Directory -Force notes | Out-Null
Set-Content notes\model_checklist.md @"

# Model Checklist – 2025-09-10

Server: http://100.109.118.90:9000

## /health

status: ok
model: qwen2.5-coder:7b

## /models

- qwen2.5-coder:7b

## .env (server)

MODEL = qwen2.5-coder:7b

## Schema defaults (server/app/schemas/completion.py)

temperature = 0.2
max_tokens = 256
stop = None (DEFAULT_STOPS: ["\n\n```", "\n\n##"])

## /complete (sample)

payload: {prefix:"def add(a,b):\n ", suffix:"\n", language:"python", temperature:0.2, max_tokens:64}
completion: <dán 1–2 dòng đầu ở đây>
"@
