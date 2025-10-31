#!/bin/bash
# Quick syntax check for modified files

echo "🔍 Checking Python syntax..."

files=(
    "server/app/services/groq.py"
    "server/app/core/config.py"
    "server/app/routers/completions.py"
    "server/app/routers/health.py"
)

all_ok=true

for file in "${files[@]}"; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo "✅ $file - OK"
    else
        echo "❌ $file - SYNTAX ERROR"
        python3 -m py_compile "$file"
        all_ok=false
    fi
done

if $all_ok; then
    echo ""
    echo "✅ All files have valid Python syntax!"
    echo ""
    echo "📝 Next steps:"
    echo "1. Push to GitHub"
    echo "2. Update Render environment variables:"
    echo "   - Set GROQ_API_KEY (from console.groq.com)"
    echo "   - Remove OLLAMA_URL, OLLAMA_API_KEY, MODEL"
    echo "   - Keep API_KEY, NUM_CTX, POSTPROCESS_ENABLED"
    echo "3. Redeploy on Render"
    echo "4. Test: curl https://your-service.onrender.com/health"
else
    echo ""
    echo "❌ Some files have syntax errors. Fix them before deploying."
    exit 1
fi
