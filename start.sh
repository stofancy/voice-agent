#!/bin/bash
# Start OpenClaw Voice
# Prerequisites: Official OpenClaw Gateway must be running first
#
# Usage: ./start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🦞 OpenClaw Voice - Join Official Gateway Network"
echo "================================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ .env created. Please edit with your Bailian API Key."
    echo ""
    echo "Edit .env and run again:"
    echo "  vim .env"
    echo "  ./start.sh"
    echo ""
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

echo "📋 Configuration:"
echo "  - Gateway Port: ${OPENCLAW_GATEWAY_PORT:-26523}"
echo "  - Voice Port: ${OPENCLAW_VOICE_PORT:-8765}"
echo "  - Bailian API Key: ${ALI_BAILIAN_API_KEY:0:15}..."
echo "  - STT Model: ${OPENCLAW_STT_MODEL:-qwen3-asr-flash}"
echo "  - TTS Model: ${OPENCLAW_TTS_MODEL:-qwen3-tts-flash}"
echo "  - TTS Voice: ${OPENCLAW_TTS_VOICE:-Cherry}"
echo "  - Network: ${OPENCLAW_NETWORK_NAME:-openclaw_default}"
echo ""

# Check if Docker is running
if ! docker info &>/dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Gateway is running
echo "🔍 Checking Gateway availability..."
if ! wget -q --spider "http://localhost:${OPENCLAW_GATEWAY_PORT:-26523}/healthz" 2>/dev/null; then
    echo "❌ Gateway is not running at localhost:${OPENCLAW_GATEWAY_PORT:-26523}"
    echo ""
    echo "Please start the official Gateway first:"
    echo "  cd ~/workspaces/openclaw"
    echo "  docker compose up -d openclaw-gateway"
    echo "  docker compose run --rm openclaw-cli onboard"
    echo ""
    exit 1
fi
echo "✅ Gateway is running!"
echo ""

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
echo "🚀 Starting Voice service..."
echo ""

$COMPOSE_CMD up -d --build

echo ""
echo "✅ Voice service started!"
echo ""
echo "📊 Status:"
$COMPOSE_CMD ps
echo ""
echo "🌐 Access:"
echo "  - OpenClaw Gateway: http://localhost:${OPENCLAW_GATEWAY_PORT:-26523}/"
echo "  - OpenClaw Voice: http://localhost:${OPENCLAW_VOICE_PORT:-8765}/"
echo ""
echo "📋 Useful commands:"
echo "  - View logs: $COMPOSE_CMD logs -f"
echo "  - Stop: $COMPOSE_CMD down"
echo "  - Restart: $COMPOSE_CMD restart"
echo "  - Status: $COMPOSE_CMD ps"
echo ""
