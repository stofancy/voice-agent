#!/bin/bash
# Start OpenClaw Voice - Bailian Edition in Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🦞 OpenClaw Voice - Bailian Edition"
echo "===================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.bailian..."
    cp .env.bailian .env
    echo "✅ .env created. Please edit with your API keys if needed."
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

# Build and start
echo "🚀 Starting Docker container..."
docker-compose -f docker-compose.bailian.yml up --build -d

echo ""
echo "✅ Container started!"
echo ""
echo "📱 Access the demo at: http://localhost:${OPENCLAW_PORT:-8765}"
echo "🔌 WebSocket: ws://localhost:${OPENCLAW_PORT:-8765}/ws"
echo ""
echo "📋 Useful commands:"
echo "  - View logs: docker-compose -f docker-compose.bailian.yml logs -f"
echo "  - Stop: docker-compose -f docker-compose.bailian.yml down"
echo "  - Restart: docker-compose -f docker-compose.bailian.yml restart"
echo ""
