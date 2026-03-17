# OpenClaw Voice v2 Discovery Report (Documentation Audit)

Date: 2026-03-17
Status: Captured before implementation

## High-priority inconsistencies
- Public docs still describe Whisper + ElevenLabs in places, while runtime implementation in this repo is Bailian/OpenClaw-first.
- Primary affected files:
  - `README.md`
  - `docs/index.html`
  - `docs/twitter-article.md`

## Why this matters
- Setup instructions and architecture expectations can become misleading.
- Environment variable expectations can drift from actual runtime behavior.

## v2 plan documentation quality
- `docs/DEVELOPMENT_PLAN_v2.md` and `docs/DESIGN_v2.md` are strong in phase/task decomposition.
- Review docs correctly highlight missing specificity around:
  - concrete test execution and coverage
  - deployment + rollback path
  - dependency/runtime risk controls

## Required documentation updates for release
1. Align stack descriptions with current implementation (Bailian STT/TTS + OpenClaw gateway fallback).
2. Add an explicit v2 websocket protocol section with backward compatibility notes.
3. Add v2 deployment and rollback checklist.
4. Add measurable verification matrix tied to pass/fail thresholds.
5. Keep v1/v2 boundaries explicit to avoid user confusion.

## Rationality summary
- The technical plan is rational and executable.
- The major weakness is doc/runtime drift, which must be treated as required work (not optional polish).
