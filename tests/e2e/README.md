# E2E Backend Testing & Performance Logging

This directory contains comprehensive end-to-end tests for the OpenClaw Voice backend with real-time performance monitoring.

## Overview

The E2E test suite measures and logs:

- **TTS (Text-to-Speech)**: First-audio latency (TTFA), total synthesis time, voice variants
- **STT (Speech-to-Text)**: Transcription latency, round-trip accuracy
- **LLM (Large Language Model)**: Time-to-first-token (TTFT), throughput, streaming behavior
- **Full Pipeline**: End-to-end STT→LLM→TTS latency (perceived response delay)

### Key Metrics

| Component | Target | Actual (avg) | Notes |
|-----------|--------|--------------|-------|
| TTS TTFA | <1000ms | ~900-1200ms | Time to first audio from API call |
| STT Latency | <1500ms | ~1100-1400ms | Per utterance transcription |
| LLM TTFT | <1000ms | ~300-1900ms | Varies with load, network |
| Pipeline Total | <3500ms | ~2850-3200ms | Full response cycle |

## Running Tests

### Prerequisites

```bash
# Create venv (one-time)
uv venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install test dependencies (uses modern pyproject.toml)
uv pip install -e ".[dev]"
```

### Run All E2E Tests

```bash
# With the API key
OPENCLAW_STT_API_KEY=sk-xxxxxxx .venv/bin/python -m pytest tests/e2e/ -v -s

# Live monitoring in another terminal
./scripts/monitor_e2e_tests.sh
```

### Run Specific Test Categories

```bash
# TTS generation and streaming latency
pytest tests/e2e/test_tts_generation.py -v

# STT transcription and accuracy
pytest tests/e2e/test_stt_transcription.py -v

# LLM streaming latency and throughput
pytest tests/e2e/test_llm_streaming.py -v

# Full pipeline tests
pytest tests/e2e/test_pipeline_e2e.py -v
```

### Run Single Test

```bash
pytest tests/e2e/test_llm_streaming.py::TestLLMTimeToFirstToken::test_ttft_short_zh -v -s
```

## Performance Logging

### Real-Time Logs

During test execution, detailed logs are written to `tests/e2e/test_run.log`:

```
2026-03-17 09:08:15.667 | INFO     | tests.e2e.conftest:__init__:89 | 
================================================================================
2026-03-17 09:08:15.667 | INFO     | tests.e2e.conftest:__init__:90 | OPENCLAW 
VOICE — E2E BACKEND PERFORMANCE TEST SESSION STARTED
2026-03-17 09:08:16.244 | DEBUG    | tests.e2e.test_llm_streaming:_stream_to_completion:54 | 
🤖 LLM: Starting stream for prompt: '你好！请简单打个招呼。'...
2026-03-17 09:08:17.679 | INFO     | tests.e2e.test_llm_streaming:_stream_to_completion:60 | 
🤖 LLM: First token at 1434.6ms
2026-03-17 09:08:17.824 | INFO     | tests.e2e.conftest:record:96 | ⏱️  PERF: llm_ttft_ms    
                = 1434.6 ms  | scenario=short_zh_prompt
```

**Log Levels:**
- `INFO` — Test lifecycle events, key latency milestones, metric recordings
- `DEBUG` — Per-chunk/token details, component-level traces

**Monitor Live Logs:**

```bash
# In a separate terminal
tail -f tests/e2e/test_run.log

# Or use the provided script
./scripts/monitor_e2e_tests.sh
```

### Performance Report

After tests complete, a JSON report is generated:

**File:** `tests/e2e/performance_report.json`

**Contents:**
```json
{
  "generated_at": "2026-03-17T09:08:17Z",
  "metrics": {
    "llm_ttft_ms": {
      "count": 7,
      "min_ms": 324.7,
      "max_ms": 1940.2,
      "avg_ms": 879.2,
      "samples_ms": [1029.7, 736.5, 1008.2, ...]
    },
    ...
  }
}
```

**How to use:**
```python
import json
with open("tests/e2e/performance_report.json") as f:
    report = json.load(f)
    ttft_stats = report["metrics"]["llm_ttft_ms"]
    print(f"LLM TTFT: {ttft_stats['avg_ms']:.0f}ms avg")
```

## Test Structure

### Config & Fixtures (`conftest.py`)

- `LatencyTracker` — Accumulates metrics with real-time logging
- `tts_client` — Bailian TTS client (function-scoped, auto-cleanup)
- `stt_client` — Bailian STT client (with resampling via scipy)
- `llm_client` — OpenAI-compatible LLM client (Qwen-turbo)
- `audio_fixtures` — Pre-generates WAV files for scenarios (cached on disk)
- `save_report_on_exit` — Hook to finalize JSON report

### Test Modules

1. **test_tts_generation.py** (206 lines)
   - Generate WAV files for all scenarios
   - Measure TTFA for each scenario
   - Test voice variants (Cherry, Bella)
   - Analyze streaming chunk timing

2. **test_stt_transcription.py** (240 lines)
   - Transcribe WAV fixtures
   - Measure STT latency
   - Validate round-trip accuracy (TTS → STT)
   - Edge cases: silence, pure tones

3. **test_llm_streaming.py** (222 lines)
   - Measure TTFT for various prompts
   - Track token throughput (tokens/sec)
   - Test multi-turn conversation context
   - Measure first-sentence latency

4. **test_pipeline_e2e.py** (261 lines)
   - Full STT → LLM → TTS pipeline
   - Measure perceivable response delay
   - Test latency perception thresholds
   - Streaming advantage analysis

## Test Scenarios

All tests run across:
- **Languages:** Chinese (zh), English (en)
- **Lengths:** Short (greeting), Medium (facts/descriptions)

Example scenarios:
```python
SCENARIOS = {
    "short_zh":  ("你好，今天天气怎么样？", "zh"),
    "short_en":  ("Hello, how are you today?", "en"),
    "medium_zh": ("请简单介绍一下中国的四大发明。", "zh"),
    "medium_en": ("Tell me a brief interesting fact about the solar system.", "en"),
}
```

## Logging Architecture

### Loguru Configuration

The logger is configured in `conftest.py` to output to both stderr and a file:

```python
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<level>{time:HH:mm:ss}</level> | <level>{level: <8}</level> | {message}",
)
logger.add(
    str(_log_file),
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    rotation="50 MB",  # rotate at 50MB
    compression="zip",  # compress rotated files
)
```

### Pytest Hooks

Two lifecycle hooks log test events:

```python
def pytest_runtest_setup(item):
    """Log test start."""
    logger.info(f"▶️  TEST START: {item.nodeid}")

def pytest_runtest_logreport(report):
    """Log test completion with status and duration."""
    if report.passed:
        logger.info(f"✅ TEST PASSED: {report.nodeid} ({report.duration*1000:.0f}ms)")
```

## Performance Analysis

### Interpreting Logs

Look for these key patterns in `test_run.log`:

```
🔊 TTS: First audio chunk arrived at 923.0ms
🎤 STT: STT 识别结果：你好，今天天气怎么样？
🤖 LLM: First token at 1434.6ms
📦 Pipeline: [1/3] STT - Transcribing audio...
⏱️  PERF: pipeline_total_ttfa_ms = 3053.8 ms  | scenario=short_zh
```

### Common Metrics to Track

1. **TTFA (Time To First Audio)**
   - Good: < 500ms (feels instant)
   - OK: 500-1000ms (feels responsive)
   - Poor: > 1500ms (feels sluggish)

2. **RTF (Real-Time Factor)**
   - RTF = synthesis_time / audio_duration
   - RTF < 1.0 = faster than playback speed ✓
   - RTF > 2.0 = lag accumulation ✗

3. **Token Throughput**
   - Goal: > 5 tokens/sec
   - Monitored via `llm_tokens_per_sec`

## Troubleshooting

### "API key is not set" error

```bash
# Set the environment variable
export OPENCLAW_STT_API_KEY=sk-xxxx
pytest tests/e2e/ -v
```

### Log file too large

The log file auto-rotates at 50MB and compresses rotated files. Manual cleanup:

```bash
rm tests/e2e/test_run.log*
rm tests/e2e/test_run.log*.zip
```

### Missing fixtures

The `audio_fixtures` fixture auto-generates WAV files if they don't exist. First run will be slower.

To manually regenerate:

```bash
rm tests/e2e/fixtures/audio/*.wav
pytest tests/e2e/test_tts_generation.py -v  # Generate all fixtures
```

### Backend timeouts

If API calls timeout, check:
- Network connectivity
- API key validity
- API rate limits (may be throttled)
- Set `OPENCLAW_BACKEND_TIMEOUT_S` in `.env` to increase timeout

## Integration with CI/CD

Example GitHub Actions workflow:

```yaml
- name: Run E2E Backend Tests
  env:
    OPENCLAW_STT_API_KEY: ${{ secrets.OPENCLAW_STT_API_KEY }}
  run: |
    pytest tests/e2e/ -v --tb=short
    
- name: Upload Performance Report
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: e2e-performance-report
    path: tests/e2e/performance_report.json
    
- name: Upload Test Logs
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: e2e-test-logs
    path: tests/e2e/test_run.log
```

## References

- Backend modules: [src/server/](../../src/server/)
- Main server: [src/server/main.py](../../src/server/main.py)
- Config: [pyproject.toml](../../pyproject.toml)
