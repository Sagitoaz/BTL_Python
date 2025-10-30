#!/bin/bash
# Script để expose Ollama local ra internet qua ngrok
# Chạy script này trên máy có Ollama đang chạy

echo "🌐 Exposing Ollama to internet via ngrok..."
echo ""
echo "Ollama local URL: http://localhost:11434"
echo ""
echo "Starting ngrok tunnel..."
echo "Press Ctrl+C to stop"
echo ""

# Kiểm tra ngrok đã cài chưa
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok chưa được cài đặt!"
    echo ""
    echo "Cài ngrok:"
    echo "1. Truy cập: https://ngrok.com/download"
    echo "2. Tải về và cài đặt"
    echo "3. Chạy: ngrok config add-authtoken <your-token>"
    echo ""
    exit 1
fi

# Chạy ngrok
ngrok http 11434

# Sau khi ngrok chạy, nó sẽ hiển thị URL dạng:
# Forwarding: https://abc123.ngrok.io -> http://localhost:11434
#
# Copy URL đó và set vào Render:
# OLLAMA_URL=https://abc123.ngrok.io
