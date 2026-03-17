#!/bin/bash
# One-click runner for backend E2E tests with performance logging.
#
# Usage:
#   ./scripts/run_e2e_backend.sh
#   ./scripts/run_e2e_backend.sh --pattern test_pipeline_e2e.py
#   ./scripts/run_e2e_backend.sh --monitor
#   ./scripts/run_e2e_backend.sh --help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

PATTERN="tests/e2e/"
MONITOR="false"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pattern)
            PATTERN="$2"
            shift 2
            ;;
        --monitor)
            MONITOR="true"
            shift
            ;;
        --help|-h)
            cat <<EOF
一键运行后端 E2E 测试

用法:
  ./scripts/run_e2e_backend.sh
  ./scripts/run_e2e_backend.sh --pattern test_pipeline_e2e.py
  ./scripts/run_e2e_backend.sh --monitor

参数:
  --pattern <path-or-glob>  指定 pytest 目标 (默认: tests/e2e/)
  --monitor                 启动实时日志监控 (tail test_run.log)
  -h, --help                显示帮助

示例:
  ./scripts/run_e2e_backend.sh --pattern tests/e2e/test_pipeline_e2e.py
  ./scripts/run_e2e_backend.sh --pattern "tests/e2e/test_llm_streaming.py::TestLLMTimeToFirstToken"
EOF
            exit 0
            ;;
        *)
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

load_env() {
    if [[ -f ".env" ]]; then
        set -a
        source .env
        set +a
        echo "✅ Loaded .env"
        return
    fi

    if [[ -f ".env.bailian" ]]; then
        set -a
        source .env.bailian
        set +a
        echo "✅ Loaded .env.bailian"
        return
    fi

    echo "❌ Missing .env and .env.bailian"
    exit 1
}

ensure_venv() {
    if [[ ! -x ".venv/bin/python" ]]; then
        echo "📦 .venv not found, creating virtual environment..."
        if command -v uv >/dev/null 2>&1; then
            uv venv .venv
        else
            python3 -m venv .venv
        fi
    fi
}

ensure_pytest() {
    if ! .venv/bin/python -m pytest --version >/dev/null 2>&1; then
        echo "📥 Installing test dependencies..."
        if command -v uv >/dev/null 2>&1; then
            uv pip install --python .venv/bin/python -r requirements.txt pytest pytest-asyncio
        else
            .venv/bin/python -m pip install -r requirements.txt pytest pytest-asyncio
        fi
    fi
}

load_env

if [[ -z "${ALI_BAILIAN_API_KEY:-}" ]]; then
    echo "❌ ALI_BAILIAN_API_KEY not found in environment (.env/.env.bailian)"
    exit 1
fi

echo ""
echo "🧪 OpenClaw Voice Backend E2E Runner"
echo "===================================="
echo "Pattern      : $PATTERN"
echo "Monitor      : $MONITOR"
echo "Python       : .venv/bin/python"
echo "Report File  : tests/e2e/performance_report.json"
echo "Log File     : tests/e2e/test_run.log"
echo ""

ensure_venv
ensure_pytest

if [[ "$MONITOR" == "true" ]]; then
    echo "📡 Starting log monitor in background..."
    ./scripts/monitor_e2e_tests.sh --follow &
    MONITOR_PID=$!
    trap 'kill $MONITOR_PID >/dev/null 2>&1 || true' EXIT
fi

echo "🚀 Running tests..."
set +e
env ALI_BAILIAN_API_KEY="$ALI_BAILIAN_API_KEY" \
    .venv/bin/python -m pytest "$PATTERN" -v -s --tb=short "${EXTRA_ARGS[@]}"
TEST_EXIT=$?
set -e

echo ""
if [[ $TEST_EXIT -eq 0 ]]; then
    echo "✅ E2E tests completed successfully"
else
    echo "❌ E2E tests failed (exit code: $TEST_EXIT)"
fi

echo "📄 Performance report: $ROOT_DIR/tests/e2e/performance_report.json"
echo "📜 Runtime logs      : $ROOT_DIR/tests/e2e/test_run.log"

echo ""
echo "Tip: view latest logs"
echo "  ./scripts/monitor_e2e_tests.sh --once"

exit $TEST_EXIT
