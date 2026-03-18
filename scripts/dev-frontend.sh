#!/bin/bash
# Start Frontend Development Server
# Port: 5173 (Vite default)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../src/client/v2-react"

echo "🦞 OpenClaw Voice - Frontend Development Server"
echo "==============================================="
echo ""

# Check node_modules
if [ ! -d "node_modules" ]; then
    echo "⚠️  node_modules not found. Installing dependencies..."
    npm install
fi

echo "✅ Dependencies ready"
echo ""
echo "🚀 Starting Vite dev server..."
echo "   - Frontend: http://localhost:5173/v2/"
echo ""
echo "⚠️  Press Ctrl+C to stop"
echo ""

# Start Vite dev server
npm run dev
