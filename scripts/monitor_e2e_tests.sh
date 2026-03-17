#!/bin/bash
# Monitor E2E backend tests in real-time

LOG_FILE="tests/e2e/test_run.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Log file not found: $LOG_FILE"
    echo ""
    echo "To start monitoring, run the tests in another terminal:"
    echo "  ALI_BAILIAN_API_KEY=sk-... python -m pytest tests/e2e/ -v"
    echo ""
    exit 1
fi

echo "📊 Monitoring OpenClaw Voice E2E Backend Tests (Ctrl+C to stop)"
echo "📋 Log file: $LOG_FILE"
echo ""
echo "❯ Live performance metrics and latency logs:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

tail -f "$LOG_FILE"
