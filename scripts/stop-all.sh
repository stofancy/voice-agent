#!/bin/bash
# Stop All Development Services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "🦞 OpenClaw Voice - Stop All Services"
echo "====================================="
echo ""

# Stop backend
echo "⏹️  Stopping backend..."
pkill -f "uvicorn src.server.main" || echo "   Backend not running"

# Stop frontend
echo "⏹️  Stopping frontend..."
pkill -f "vite" || echo "   Frontend not running"

# Stop Docker containers (optional)
echo ""
echo "🐳 Docker containers:"
read -p "   Stop Gateway container? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker compose stop
    echo "✅ Containers stopped"
else
    docker compose ps
    echo "✅ Containers still running"
fi

echo ""
echo "✅ All services stopped"
