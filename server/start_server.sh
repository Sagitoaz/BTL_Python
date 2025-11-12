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
