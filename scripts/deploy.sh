#!/bin/bash
# Production Deployment Script
# Deploys: Gateway + Backend + Frontend (3 containers)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "🦞 OpenClaw Voice - Production Deployment"
echo "=========================================="
echo ""
echo "📦 Architecture:"
echo "   - openclaw-gateway (26523)"
echo "   - openclaw-voice-backend (8765)"
echo "   - openclaw-voice-frontend (8764)"
echo ""

# Check environment
if [ ! -f ".env" ]; then
    echo "⚠️  .env not found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ .env created. Please edit with your Bailian API Key."
    echo ""
fi

# Build and deploy
echo "🔨 Building Docker images..."
docker compose build

echo ""
echo "🚀 Starting services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Status:"
docker compose ps

echo ""
echo "🌐 Access:"
echo "  - Frontend: http://localhost:${OPENCLAW_FRONTEND_PORT:-8764}/"
echo "  - Backend API: http://localhost:${OPENCLAW_BACKEND_PORT:-8765}/"
echo "  - Gateway: http://localhost:26523/"
echo ""
echo "📋 Useful commands:"
echo "  - View logs: docker compose logs -f"
echo "  - Stop: docker compose down"
echo "  - Restart: docker compose restart"
echo "  - Rebuild: ./scripts/deploy.sh"
echo ""
