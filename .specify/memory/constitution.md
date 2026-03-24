# OpenClaw Voice Constitution

## Core Principles

### I. Single Responsibility & Library Encapsulation
Every module and class MUST have one clear, focused responsibility. New functionality starts as a standalone module in `src/server/` with clear boundaries. Providers (TTS, STT, LLM) follow factory patterns and expose consistent interfaces. No God classes or multi-purpose utilities.

### II. Test-First Development (NON-NEGOTIABLE)
All new features and bug fixes MUST have tests written before implementation. The Red-Green-Refactor cycle is mandatory: tests fail first (Red), then minimal implementation passes (Green), then refine (Refactor). Unit tests cover individual modules; integration tests verify provider contracts.

### III. Streaming-First Performance
Real-time voice interaction demands streaming architecture. LLM token generation and TTS audio output MUST run in parallel to minimize perceived latency. Audio buffers MUST be appropriately sized to balance responsiveness and quality. VAD (Voice Activity Detection) MUST filter noise before STT to preserve bandwidth.

### IV. WebSocket State Machine Integrity
Connection states (IDLE/LISTENING/PROCESSING/SPEAKING) MUST follow strict transition rules. Interrupted turns MUST cancel in-flight requests and reset state cleanly. All message types MUST be handled via typed dispatch in `message_router.py`; no ad-hoc message handling.

### V. Observability & Structured Logging
All operations MUST emit structured logs with consistent format. Key events (turn start/end, VAD detection, TTS segment, error conditions) MUST be logged at appropriate levels. Logs MUST be debuggable in production; avoid sensitive data in logs.

## Performance Standards

### Latency Requirements
- STT transcription: <500ms for typical utterances
- TTS time buffer: configurable via `OPENCLAW_TTS_TIME_BUFFER_SECONDS` (default 0.5s)
- Parallel LLM+TTS streaming achieves ~50% faster perceived response
- Target end-to-end latency (speak → respond) <2s for simple queries

### Resource Constraints
- Memory usage MUST stay under 200MB baseline
- Audio buffer sizes MUST be bounded; no unbounded growth
- WebSocket connections MUST be properly cleaned up on disconnect

## Development Workflow

### Quality Gates
All pull requests MUST verify:
1. Unit tests pass: `.venv/bin/python -m pytest tests/unit/`
2. Code linting passes (if configured)
3. No new debug logs or console statements in production paths

### Code Review Requirements
- Single Responsibility: each PR addresses one concern
- Tests included for new functionality
- Migration/rollback plan for breaking changes

### Architecture Decisions
Complex patterns (Repository, Observer, etc.) MUST be justified in code review. Prefer composition over inheritance. YAGNI: do not add complexity speculatively.

## Governance

This constitution supersedes informal practices. Amendments require:
1. Documentation of proposed change and rationale
2. Review and approval from at least one maintainer
3. Updated constitution committed alongside implementation

**Version**: 1.0.0 | **Ratified**: 2026-03-24 | **Last Amended**: 2026-03-24
