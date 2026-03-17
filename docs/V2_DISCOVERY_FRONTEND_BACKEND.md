# OpenClaw Voice v2 Discovery Report (Frontend + Backend)

Date: 2026-03-17
Status: Captured during implementation kickoff

## Frontend current state at discovery
- `src/client/v2/index.html` existed with page skeleton:
  - top bar, conversation area, TALK button, interrupt button, history button, speaking indicator
- The page referenced missing assets at discovery time:
  - `css/main.css`, `css/animation.css`, `css/mobile.css`
  - `js/app.js`, `js/vad.js`, `js/tts.js`, `js/ui.js`
  - `assets/favicon.svg`
- `src/client/index.html` had reusable working patterns for:
  - websocket connect/auth/reconnect
  - audio capture and base64 transport
  - playback queue handling
  - transcript rendering

## Backend protocol baseline at discovery
Client -> Server:
- `start_listening`
- `audio`
- `stop_listening`
- `ping`

Server -> Client:
- `listening_started`
- `transcript`
- `subtitle_chunk`
- `audio_chunk`
- `response_complete`
- `listening_stopped`
- `vad_status`
- `pong`
- fallback: `response_chunk`

## Risks and blockers found at discovery
- `src/server/main.py` used undefined runtime variables:
  - `TTS_TIME_BUFFER_SECONDS`
  - `TTS_DATA_BUFFER_SIZE`
  - `time_buffer_elapsed_ms`
- `src/server/main.py` had duplicate/trailing corrupted content near file tail.
- `src/server/bailian_tts.py` used `start_time` without guaranteed initialization in streaming logs.

## Required backend extensions for v2
- Add page route `/v2` and `/v2/` -> `src/client/v2/index.html`.
- Keep `/ws` and `/voice/ws` behavior backward compatible.
- Add additive v2 events:
  - inbound: `interrupt`
  - outbound: `tts_start`, `tts_end`, `interrupt_ack`, `interrupt_complete`
- Add connection state guard to reduce overlap/race issues.

## Test compatibility notes
- Existing tests in `tests/test_server.py` should continue to pass if new events are additive.
- v2 event assertions should be added as separate tests, not by changing baseline semantics.
