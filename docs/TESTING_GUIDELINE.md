# OpenClaw Voice Testing Guideline

Last updated: 2026-03-17

## 1. Scope

This guideline defines the recommended test workflow for OpenClaw Voice backend quality validation, with emphasis on:

- Real provider E2E tests (Bailian STT / LLM / TTS)
- Real-time latency observation
- Repeatable execution and reporting

Current phase focuses on **backend** only. Frontend E2E is out of scope for this document.

---

## 2. Test Levels

### Level A — Smoke / Basic Server Health

Purpose: verify service can start and basic websocket flow works.

Run:

```bash
.venv/bin/python -m pytest tests/test_server.py -v
```

Pass criteria:
- All tests pass
- Server startup is successful
- Ping/pong and start/stop listening flow works

### Level B — Backend Component E2E

Purpose: validate each core backend component with real provider calls.

Modules:
- `tests/e2e/test_stt_transcription.py`
- `tests/e2e/test_llm_streaming.py`
- `tests/e2e/test_tts_generation.py`

Pass criteria:
- No component test failures
- Latency logs generated in real-time
- Performance report generated at end

### Level C — Full Pipeline E2E

Purpose: verify complete `STT -> LLM -> TTS` behavior.

Module:
- `tests/e2e/test_pipeline_e2e.py`

Pass criteria:
- End-to-end tests pass
- Pipeline timing metrics are present in report and runtime logs

---

## 3. One-Click Execution (Recommended)

Use the one-click script:

```bash
./scripts/run_e2e_backend.sh
```

Useful options:

```bash
# run specific file/class/case
./scripts/run_e2e_backend.sh --pattern tests/e2e/test_pipeline_e2e.py
./scripts/run_e2e_backend.sh --pattern "tests/e2e/test_llm_streaming.py::TestLLMTimeToFirstToken"

# run with live monitor
./scripts/run_e2e_backend.sh --monitor
```

What this script does automatically:
- Loads `.env` (fallback `.env.bailian`)
- Checks `ALI_BAILIAN_API_KEY`
- Ensures `.venv` and pytest dependencies
- Runs pytest with useful output flags
- Prints report/log paths at the end

---

## 4. Environment Requirements

Required:
- Python 3.10+
- Valid `ALI_BAILIAN_API_KEY`
- Network access to provider endpoints

Recommended:
- `uv` available (faster env/dependency handling)

API key source priority:
1. `.env`
2. `.env.bailian`

---

## 5. Real-Time Latency Logging

Runtime log file:
- `tests/e2e/test_run.log`

Performance summary file:
- `tests/e2e/performance_report.json`

Monitor commands:

```bash
# auto mode: follow if tests running, otherwise print recent logs and exit
./scripts/monitor_e2e_tests.sh

# force follow
./scripts/monitor_e2e_tests.sh --follow

# one-shot
./scripts/monitor_e2e_tests.sh --once
```

Expected logged dimensions:
- STT latency
- LLM TTFT / first sentence / total generation
- TTS TTFA / stream chunk timing / total synthesis
- Pipeline total TTFA (`STT + LLM_TTFT + TTS_TTFA`)

---

## 6. Execution Order (CI/Manual)

Recommended order:

1. `tests/test_server.py`
2. `tests/e2e/test_stt_transcription.py`
3. `tests/e2e/test_llm_streaming.py`
4. `tests/e2e/test_tts_generation.py`
5. `tests/e2e/test_pipeline_e2e.py`

For local fast validation, run:

```bash
./scripts/run_e2e_backend.sh --pattern tests/e2e/test_pipeline_e2e.py
```

For release validation, run full suite:

```bash
./scripts/run_e2e_backend.sh --monitor
```

---

## 7. Failure Triage Rules

If test fails, classify first:

1. **Environment issue**
   - Missing key
   - DNS/network/provider timeout
   - Missing dependency

2. **Test harness issue**
   - Fixture lifecycle
   - Session/event-loop cleanup
   - Log/report hook failure

3. **Product/backend issue**
   - Incorrect STT/LLM/TTS response handling
   - Streaming protocol regression
   - Latency spike due to logic changes

Minimal triage checklist:
- Re-run failed case once
- Check `tests/e2e/test_run.log` around failure timestamp
- Check provider response in logs
- Confirm whether failure is deterministic

---

## 8. Reporting Standard

When posting test result in PR or handover, include:

- Command used
- Pass/fail summary (`X passed, Y failed`)
- Report file path
- 3 key latency metrics (avg):
  - `stt_latency_ms`
  - `llm_ttft_ms`
  - `pipeline_total_ttfa_ms`
- Any abnormal outlier and probable reason

Example:

```text
Command: ./scripts/run_e2e_backend.sh --monitor
Result: 30 passed, 0 failed
Report: tests/e2e/performance_report.json
Avg STT: 1243ms, Avg LLM TTFT: 876ms, Avg Pipeline TTFA: 3054ms
Notes: no deterministic failures, occasional provider-side jitter observed
```

---

## 9. Commit Hygiene for Test Artifacts

Do commit:
- Test source files (`tests/e2e/*.py`)
- Script changes (`scripts/*.sh`)
- Guideline/docs updates

Do **not** commit routine runtime artifacts unless explicitly requested:
- `tests/e2e/test_run.log*`
- Refreshed audio fixtures from ad-hoc reruns
- Temporary local outputs

---

## 10. Definition of Done (Backend Testing Phase)

Backend testing phase is considered complete when:
- One-click script executes successfully
- Full backend E2E suite passes with valid key
- Real-time logs are available during execution
- Performance report is generated and reviewable
- Guideline is updated and aligned with current workflow
