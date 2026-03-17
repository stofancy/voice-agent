#!/bin/bash
# Monitor E2E backend test logs.
#
# Usage:
#   ./scripts/monitor_e2e_tests.sh           # auto mode (follow if pytest running)
#   ./scripts/monitor_e2e_tests.sh --follow  # always follow (tail -f)
#   ./scripts/monitor_e2e_tests.sh --once    # print recent logs and exit

set -e

LOG_FILE="tests/e2e/test_run.log"
MODE="auto"

if [ "${1:-}" = "--follow" ]; then
    MODE="follow"
elif [ "${1:-}" = "--once" ]; then
    MODE="once"
elif [ -n "${1:-}" ]; then
    echo "Unknown option: $1"
    echo "Usage: $0 [--follow|--once]"
    exit 2
fi

if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Log file not found: $LOG_FILE"
    echo ""
    echo "Run tests first to generate logs:"
    echo "  ALI_BAILIAN_API_KEY=*** .venv/bin/python -m pytest tests/e2e/ -v -s"
    exit 1
fi

echo "📊 OpenClaw Voice E2E log monitor"
echo "📋 Log file: $LOG_FILE"
echo ""

if pgrep -f "pytest tests/e2e|python -m pytest tests/e2e" >/dev/null 2>&1; then
    PYTEST_RUNNING="yes"
else
    PYTEST_RUNNING="no"
fi

if [ "$MODE" = "once" ]; then
    echo "Mode: once (show recent logs and exit)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -n 200 "$LOG_FILE"
    exit 0
fi

if [ "$MODE" = "follow" ] || [ "$PYTEST_RUNNING" = "yes" ]; then
    echo "Mode: follow (Ctrl+C to stop)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -n 120 -f "$LOG_FILE"
    exit 0
fi

echo "Mode: auto"
echo "No active pytest E2E process detected, showing recent logs and exiting."
echo "Use '--follow' if you want to keep waiting for future log updates."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tail -n 200 "$LOG_FILE"
