#!/bin/bash
# Start OpenClaw Voice (Full Stack: Gateway + Voice)
# Self-contained deployment - does NOT touch host OpenClaw config

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🦞 OpenClaw Voice - Self-Contained Deployment"
echo "=============================================="
echo ""
echo "⚠️  This deployment is ISOLATED and does NOT use your host OpenClaw config."
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.full..."
    cp .env.full .env
    echo "✅ .env created. Please edit with your Bailian API Key."
    echo ""
fi

# Load environment variables
set -a
source .env
set +a

echo "📋 Configuration:"
echo "  - Gateway Port: ${OPENCLAW_GATEWAY_PORT:-18789}"
echo "  - Voice Port: ${OPENCLAW_VOICE_PORT:-8765}"
echo "  - Gateway Bind: ${OPENCLAW_GATEWAY_BIND:-lan}"
echo "  - Bailian API Key: ${ALI_BAILIAN_API_KEY:0:15}..."
echo "  - STT Model: ${OPENCLAW_STT_MODEL:-qwen3-asr-flash}"
echo "  - TTS Model: ${OPENCLAW_TTS_MODEL:-qwen3-tts-flash}"
echo "  - TTS Voice: ${OPENCLAW_TTS_VOICE:-Cherry}"
echo "  - Config Volume: openclaw-gateway-data (isolated)"
echo ""

# Check if Docker is running
if ! docker info &>/dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Use docker compose (v2) or docker-compose (v1)
if docker compose version &>/dev/null; then
    COMPOSE_CMD="docker compose"
elif docker-compose version &>/dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Build and start
echo "🚀 Starting services..."
echo ""

$COMPOSE_CMD -f docker-compose.full.yml -p openclaw-voice up -d --build

echo ""
echo "✅ Services started!"
echo ""
echo "📊 Status:"
$COMPOSE_CMD -f docker-compose.full.yml -p openclaw-voice ps
echo ""
echo "🌐 Access:"
echo "  - OpenClaw Control UI: http://localhost:${OPENCLAW_GATEWAY_PORT:-18789}/"
echo "  - OpenClaw Voice UI: http://localhost:${OPENCLAW_VOICE_PORT:-8765}/"
echo ""
echo "📋 Useful commands:"
echo "  - View logs: $COMPOSE_CMD -f docker-compose.full.yml -p openclaw-voice logs -f"
echo "  - Stop: $COMPOSE_CMD -f docker-compose.full.yml -p openclaw-voice down"
echo "  - Restart: $COMPOSE_CMD -f docker-compose.full.yml -p openclaw-voice restart"
echo ""
