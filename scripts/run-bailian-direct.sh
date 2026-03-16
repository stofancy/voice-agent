#!/bin/bash
# Start OpenClaw Voice - Bailian Edition (Direct Run - No Docker)
# Fallback when Docker Hub is unavailable

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🦞 OpenClaw Voice - Bailian Edition (Direct Run)"
echo "================================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.bailian..."
    cp .env.bailian .env
    echo "✅ .env created"
    echo ""
fi

# Load environment variables
set -a
source .env
set +a

echo "🔧 Configuration:"
echo "  - Bailian API Key: ${ALI_BAILIAN_API_KEY:0:10}..."
echo "  - Gateway URL: ${OPENCLAW_GATEWAY_URL:-Not set}"
echo "  - STT Model: ${OPENCLAW_STT_MODEL:-qwen3-asr-flash}"
echo "  - TTS Model: ${OPENCLAW_TTS_MODEL:-qwen3-tts-flash}"
echo "  - TTS Voice: ${OPENCLAW_TTS_VOICE:-Cherry}"
echo "  - Port: ${OPENCLAW_PORT:-8765}"
echo ""

# Check Python
echo "🐍 Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION"
echo ""

# Create venv if not exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
    echo ""
fi

# Activate venv
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Start server
echo "🚀 Starting server..."
echo ""
echo "📱 Web UI: http://localhost:${OPENCLAW_PORT:-8765}"
echo "🔌 WebSocket: ws://localhost:${OPENCLAW_PORT:-8765}/ws"
echo ""
echo "⚠️  Press Ctrl+C to stop"
echo ""

python -m uvicorn src.server.main:app --host 0.0.0.0 --port ${OPENCLAW_PORT:-8765}
