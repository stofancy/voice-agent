#!/bin/bash
# Start Backend Development Server
# Port: 8766 (to avoid conflict with Docker production on 8765)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "🦞 OpenClaw Voice - Backend Development Server"
echo "=============================================="
echo ""

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Creating..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Check .env.local
if [ ! -f ".env.local" ]; then
    echo "⚠️  .env.local not found. Creating from template..."
    cat > .env.local << 'EOF'
# Bailian API Key (required)
OPENCLAW_BAILIAN_API_KEY=sk-your-key-here

# Backend Configuration
OPENCLAW_HOST=0.0.0.0
OPENCLAW_PORT=8766
OPENCLAW_STT_MODEL=qwen3-asr-flash
OPENCLAW_STT_LANGUAGE=zh
OPENCLAW_TTS_MODEL=qwen3-tts-flash
OPENCLAW_TTS_VOICE=Cherry
OPENCLAW_TTS_LANGUAGE=Chinese

# Gateway (Docker container)
OPENCLAW_GATEWAY_URL=http://localhost:26523
OPENCLAW_GATEWAY_TOKEN=openclaw-your-gateway-token-here
EOF
    echo "✅ .env.local created. Please edit with your Bailian API Key."
    exit 1
fi

echo "✅ Environment ready"
echo ""
echo "🚀 Starting backend server..."
echo "   - Health: http://localhost:8766/health"
echo "   - API Docs: http://localhost:8766/docs"
echo ""
echo "⚠️  Press Ctrl+C to stop"
echo ""

# Start server with auto-reload
python -m uvicorn src.server.main:app --host 0.0.0.0 --port 8766 --reload
