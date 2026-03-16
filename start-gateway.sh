#!/bin/bash
# Start Official OpenClaw Gateway
# This script starts the official Gateway without modifying the repository
#
# Usage: ./start-gateway.sh

set -e

OFFICIAL_DIR="$HOME/workspaces/openclaw"
VOICE_DIR="$HOME/workspaces/openclaw-voice"

echo "🦞 OpenClaw Gateway - Official Deployment"
echo "========================================="
echo ""

cd "$OFFICIAL_DIR"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ .env created."
    echo ""
fi

# Load environment variables
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Set custom ports if not already set
export OPENCLAW_GATEWAY_PORT=${OPENCLAW_GATEWAY_PORT:-26523}
export OPENCLAW_BRIDGE_PORT=${OPENCLAW_BRIDGE_PORT:-26524}
export OPENCLAW_GATEWAY_BIND=${OPENCLAW_GATEWAY_BIND:-lan}
export OPENCLAW_IMAGE=${OPENCLAW_IMAGE:-openclaw:local}

echo "📋 Configuration:"
echo "  - Gateway Port: $OPENCLAW_GATEWAY_PORT"
echo "  - Bridge Port: $OPENCLAW_BRIDGE_PORT"
echo "  - Gateway Bind: $OPENCLAW_GATEWAY_BIND"
echo "  - Image: $OPENCLAW_IMAGE"
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

# Start Gateway
echo "🚀 Starting Gateway..."
$COMPOSE_CMD up -d openclaw-gateway

echo ""
echo "⏳ Waiting for Gateway to be healthy..."
sleep 10

# Check Gateway status
if ! docker ps --format '{{.Names}}' | grep -q "openclaw-gateway"; then
    echo "❌ Gateway failed to start!"
    docker compose logs openclaw-gateway | tail -20
    exit 1
fi

echo "✅ Gateway is running!"
echo ""

# Run onboarding if config doesn't exist
echo "📝 Checking if onboarding is needed..."
if ! docker compose run --rm openclaw-cli gateway probe 2>/dev/null; then
    echo ""
    echo "🔧 Running onboarding wizard..."
    echo "Please follow the prompts to configure your Gateway."
    echo ""
    docker compose run --rm openclaw-cli onboard
fi

echo ""
echo "📊 Gateway Status:"
$COMPOSE_CMD ps openclaw-gateway
echo ""
echo "🌐 Access:"
echo "  - Gateway: http://localhost:$OPENCLAW_GATEWAY_PORT/"
echo "  - Health: http://localhost:$OPENCLAW_GATEWAY_PORT/healthz"
echo ""
echo "✅ Gateway setup complete!"
echo ""
echo "Next step: Start Voice service"
echo "  cd $VOICE_DIR"
echo "  ./start.sh"
echo ""
