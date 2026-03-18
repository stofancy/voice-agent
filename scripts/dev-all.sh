#!/bin/bash
# Start All Development Services
# - Backend: port 8766
# - Frontend: port 5173
# - Gateway: Docker container (port 26523)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "🦞 OpenClaw Voice - Full Development Environment"
echo "================================================"
echo ""

# Check Gateway container
echo "📦 Checking Gateway container..."
if docker compose ps | grep -q "openclaw-gateway.*Up"; then
    echo "✅ Gateway already running"
else
    echo "⚠️  Gateway not running. Starting..."
    docker compose up -d openclaw-gateway
    sleep 5
fi

echo ""
echo "🔨 Starting backend (port 8766)..."
source .venv/bin/activate
python -m uvicorn src.server.main:app --host 0.0.0.0 --port 8766 --reload &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8766/health > /dev/null 2>&1; then
        echo "✅ Backend ready"
        break
    fi
    sleep 1
done

echo ""
echo "🎨 Starting frontend (port 5173)..."
cd src/client/v2-react
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "=============================================="
echo "✅ All services started!"
echo ""
echo "🌐 Access:"
echo "  - Frontend: http://localhost:5173/v2/"
echo "  - Backend API: http://localhost:8766/"
echo "  - Health: http://localhost:8766/health"
echo "  - Gateway: http://localhost:26523/"
echo ""
echo "📋 PIDs:"
echo "  - Backend: $BACKEND_PID"
echo "  - Frontend: $FRONTEND_PID"
echo ""
echo "⚠️  To stop all services:"
echo "  ./scripts/stop-all.sh"
echo "  or press Ctrl+C (may not stop background processes)"
echo ""

# Wait for both processes
wait
