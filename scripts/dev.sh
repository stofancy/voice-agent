#!/bin/bash
# Development Mode Script
# Starts frontend (Vite HMR) and backend (uvicorn --reload)
# Connects to Docker OpenClaw Gateway

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "🦞 OpenClaw Voice - Development Mode"
echo "======================================"
echo ""

# Load environment variables
if [ -f ".env.development" ]; then
    export $(cat .env.development | grep -v '^#' | xargs)
elif [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "📋 Configuration:"
echo "  - Gateway URL: ${OPENCLAW_GATEWAY_URL:-http://localhost:26523}"
echo "  - Voice Port: ${OPENCLAW_VOICE_PORT:-8766}"
echo "  - STT Model: ${OPENCLAW_STT_MODEL:-qwen3-asr-flash}"
echo "  - TTS Model: ${OPENCLAW_TTS_MODEL:-qwen3-tts-flash}"
echo ""

# Check if Docker Gateway is running
if ! curl -s "${OPENCLAW_GATEWAY_URL:-http://localhost:26523}/health" > /dev/null 2>&1; then
    echo "⚠️  Warning: OpenClaw Gateway not responding at ${OPENCLAW_GATEWAY_URL:-http://localhost:26523}"
    echo "   Please start Docker Gateway first:"
    echo "   docker compose up -d openclaw-gateway"
    echo ""
fi

# Start backend in background
echo "🚀 Starting backend (uvicorn --reload)..."
cd src/server
nohup python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port ${OPENCLAW_VOICE_PORT:-8766} \
    --reload \
    --log-level info \
    > ../../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ../..

echo "✅ Backend started (PID: $BACKEND_PID)"
echo "   Logs: logs/backend.log"
echo "   URL: http://localhost:${OPENCLAW_VOICE_PORT:-8766}/"
echo ""

# Start frontend
echo "🎨 Starting frontend (Vite HMR)..."
cd src/client/v2-react
npm run dev -- --host 0.0.0.0 --port 5173
FRONTEND_EXIT_CODE=$?
cd ../../..

# Cleanup
echo ""
echo "🛑 Stopping backend..."
kill $BACKEND_PID 2>/dev/null || true

exit $FRONTEND_EXIT_CODE
