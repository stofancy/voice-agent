# OpenClaw Voice v2 Full-Scope Execution Plan

Date: 2026-03-17
Scope: Full feature set (no MVP reduction)

## Goal
Deliver v2 according to existing design/development docs as a full feature set, while preserving v1 compatibility and reducing implementation risk through phased execution.

## Constraints
- Keep v1 URLs and behavior intact.
- New protocol events must be additive (no breaking replacements).
- Stabilize backend runtime before frontend feature expansion.

## Phase A — Baseline stabilization (blocker phase)
1. Fix server runtime blockers in `src/server/main.py`:
   - define TTS buffer constants
   - fix invalid logging variable
   - remove duplicated/trailing corruption
2. Fix `start_time` streaming-log issue in `src/server/bailian_tts.py`.
3. Preserve baseline websocket compatibility used by current tests.
4. Add defensive session state guard (IDLE/LISTENING/PROCESSING/SPEAKING).

## Phase B — Routing and protocol extension
1. Add `/v2` and `/v2/` routes returning `src/client/v2/index.html`.
2. Keep `/ws` and `/voice/ws` as canonical websocket endpoints.
3. Add v2-compatible events:
   - inbound: `interrupt`
   - outbound: `interrupt_ack`, `interrupt_complete`, `tts_start`, `tts_end`
4. Ensure cancellation flow is safe when active generation/TTS is interrupted.

## Phase C — Frontend v2 scaffolding
Create and wire missing v2 assets:
- CSS: `src/client/v2/css/main.css`, `animation.css`, `mobile.css`
- JS: `src/client/v2/js/app.js`, `vad.js`, `tts.js`, `ui.js`, `sanitize.js`
- Components: `src/client/v2/components/MessageBubble.js`, `TalkButton.js`, `InterruptButton.js`
- Block components: `src/client/v2/components/blocks/*`

## Phase D — Core features (F1/F2/F4)
1. F1 user speech stops playback:
   - browser-side VAD transitions
   - immediate local TTS stop when user starts speaking
2. F2 interrupt button:
   - UI trigger -> websocket `interrupt`
   - local queue stop + server completion handling
3. F4 talk animation:
   - animate on `tts_start`
   - stop on `tts_end`

## Phase E — Rich subtitles (F3 full scope)
1. Message rendering pipeline for text/image/link/video/html blocks.
2. Markdown parsing + sanitization before HTML insertion.
3. Scroll/history behavior optimization with graceful fallback.
4. Handle legacy and streaming response forms.

## Phase F — UI redesign completion (F6)
1. Dark theme + glass card treatment using v2 CSS system.
2. Responsive behavior for mobile/tablet/desktop.
3. Dynamic top-bar hide/show and message density controls.

## Phase G — Testing and validation
1. Keep `tests/test_server.py` passing.
2. Add v2 protocol tests for interrupt and tts lifecycle events.
3. Manual matrix:
   - push-to-talk
   - interrupt latency
   - VAD interruption behavior
   - rich content rendering
   - reconnect behavior
4. Regression checks for `/`, `/voice`, `/v2`.

## Phase H — Documentation alignment
1. Align runtime stack messaging in:
   - `README.md`
   - `docs/index.html`
   - `docs/twitter-article.md`
2. Add protocol/deployment/rollback/testing details for v2.
3. Capture rollout and rollback notes.

## Verification checklist
- Run problems check for edited files after each phase.
- Run backend tests after server changes.
- Confirm route availability (`/`, `/voice`, `/v2`).
- Confirm protocol event order and interruption behavior.
- Confirm acceptance behavior for F1/F2/F3/F4/F6.

## Decision log
- Full scope delivery by request.
- Backward compatibility is mandatory.
- Additive protocol evolution only.
- Documentation alignment is release-critical work.
