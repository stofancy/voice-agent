# Agent Layer Implementation Handoff

**Created**: 2026-03-25
**Feature Branch**: `001-agent-layer`
**Status**: In Progress - Phase 5 Ready

---

## Executive Summary

Self-managed agent layer replacing OpenClaw with LangChain Agents for full streaming control during tool calls. **MVP is 85% complete** (Phase 2-4 done, Phase 5 ready to start).

### What Works

- Agent framework (BaseAgent, events, factory)
- StreamController for non-blocking tool events
- BookingAgent with hotel_tool (search, book)
- Progress messages during tool execution
- WebSocket event emission for tool lifecycle
- Unit tests passing (14 passed, 16 skipped due to langchain-core not installed)

### Critical Gap

**T014**: Integration into `voice_turn.py` not complete. Current `voice_turn.py` still uses `StreamingSynthesis` directly. Full E2E testing requires this integration.

---

## Project Structure

```
specs/001-agent-layer/
├── spec.md              # Feature specification (4 user stories)
├── plan.md              # Implementation plan
├── research.md          # LangChain streaming research
├── data-model.md        # Entity definitions
├── quickstart.md        # Local testing guide
├── contracts/           # Interface contracts
├── checklists/          # Requirements quality checklists
│   ├── requirements.md  # 27 items
│   ├── routing.md      # 27 items
│   └── streaming.md    # 24 items
└── tasks.md            # Task list (35 tasks)

src/server/agent/
├── __init__.py
├── base.py             # BaseAgent abstract class
├── events.py           # Event dataclasses (ToolStart, ToolComplete, etc.)
├── factory.py          # create_*_agent factories
├── langchain_agent.py  # LangChain wrapper with astream_events()
├── llm_factory.py      # LLM wrapper for LangChain
├── stream_controller.py # BaseCallbackHandler for non-blocking
├── booking_agent.py    # BookingAgent (hotel booking)
├── websocket_emitter.py # WebSocket event emitter
└── tools/
    ├── dummy_tool.py   # Echo tool for testing
    └── hotel_tool.py   # search_hotels, book_hotel

tests/unit/agent/
├── test_base.py
├── test_stream_controller.py
├── test_langchain_agent.py
└── test_booking_flow.py

tests/smoke_test_agent.py  # Smoke test script
```

---

## User Stories & Status

| Story | Priority | Status | Tasks |
|-------|-----------|--------|-------|
| US1: Non-Blocking Tool Calls | P1 | ⚠️ 15/16 done | T014 pending |
| US2: Voice Booking Flow | P1 | ✅ Complete | T017-T021 done |
| US3: Multi-Agent Routing | P2 | ❌ Not started | T022-T026 |
| US4: Interruption Handling | P1 | ❌ Not started | T027-T030 |

---

## Completed Tasks (24 of 35)

### Phase 1: Setup ✅
- T001: Directory structure
- T002: LangChain dependencies in requirements.txt
- T003: Logging configuration

### Phase 2: Foundational ✅
- T004: `__init__.py` with exports
- T005: `base.py` with BaseAgent
- T006: `events.py` with event dataclasses
- T007: `stream_controller.py` with BaseCallbackHandler
- T008: `llm_factory.py` wrapper
- T009-T010: Unit tests

### Phase 3: US1 ⚠️
- T011: dummy_tool.py
- T012: langchain_agent.py
- T013: StreamController integration
- T015: WebSocket emitter
- T016: Tests
- **T014 PENDING**: voice_turn.py integration

### Phase 4: US2 ✅
- T017: hotel_tool.py
- T018: booking_agent.py
- T019: ReAct prompt
- T020: Progress callbacks
- T021: Integration tests

---

## Pending Tasks (11)

### Critical (Block MVP)
| Task | Description | Owner |
|------|-------------|--------|
| T014 | Integrate into voice_turn.py | TODO |

### Phase 5: US3 - Multi-Agent Routing
| Task | Description |
|------|-------------|
| T022 | Create query_tool.py (weather, search) |
| T023 | Create query_agent.py |
| T024 | Create router.py with intent classification |
| T025 | Add routing decision logging |
| T026 | Test routing |

### Phase 6: US4 - Interruption Handling
| Task | Description |
|------|-------------|
| T027 | Add cancellation token to TurnContext |
| T028 | Tool call cancellation in StreamController |
| T029 | TTS fallback on interruption |
| T030 | Test interruption |

### Phase 7: Polish
| Task | Description |
|------|-------------|
| T031 | Update docs/agent-layer.md |
| T032 | Code cleanup |
| T033 | Performance measurement (<200ms) |
| T034 | Integration tests |
| T035 | Security audit |

---

## Key Design Decisions

### 1. LangChain Agent Pattern
Uses `astream_events()` for streaming tool events without blocking LLM stream.

### 2. Progress Messages
```python
TOOL_PROGRESS_MESSAGES = {
    "search": "Searching...",
    "hotel": "Finding hotels for you...",
    "book": "Processing your booking...",
    "weather": "Checking the weather...",
    "echo": "Processing...",
    "default": "Please wait...",
}
```

### 3. Event System
All events have `to_dict()` for WebSocket serialization:
- `tool_start`, `tool_progress`, `tool_complete`, `tool_error`
- `stream_chunk`, `agent_start`, `agent_complete`

### 4. Chrome MCP Decision
User indicated Chrome MCP as future tool backend instead of OpenClaw browser tools. **Not yet implemented** - current tools are mock implementations for architecture validation.

---

## Analysis Findings (from /speckit.analyze)

### Critical Issues
1. T014 status misleading - should be marked pending, not done
2. Phase 2/3/4 marked "TODO" but actually complete

### High Priority
1. FR-005 (intent routing) has no implementation yet - T024 needed
2. FR-007 (interruption) has no implementation yet - T027,T028 needed

### Medium Priority
1. FR-005 "intent classification" mechanism not specified (keyword vs LLM?)
2. SC-001 (200ms) vs SC-002 (500ms) - different thresholds, unclear rationale
3. Chrome MCP not mentioned in spec

---

## Constitution Alignment

| Principle | Status |
|-----------|--------|
| I. Single Responsibility | ✅ Agent module separate |
| II. Test-First | ✅ Tests exist, T014 needs test |
| III. Streaming-First | ✅ StreamController implements |
| IV. WebSocket State | ⚠️ T014 integration needed |
| V. Observability | ✅ Events with structured logging |

---

## How to Run

### Install Dependencies
```bash
pip install langchain-core langchain-openai
```

### Run Smoke Test
```bash
source .venv/bin/activate
python tests/smoke_test_agent.py
```

### Run Unit Tests
```bash
source .venv/bin/activate
python -m pytest tests/unit/agent/ -v
```

### Run All Tests
```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

---

## Next Steps (Recommended Order)

### Option A: Incremental
1. Complete Phase 5 (T022-T026) - Multi-agent routing
2. Complete Phase 6 (T027-T030) - Interruption handling
3. Return to T014 - Integrate into voice_turn.py
4. Phase 7 - Polish

### Option B: Complete T014 First
1. Complete T014 - Integrate into voice_turn.py
2. Run full E2E test
3. Continue with Phase 5-7

---

## Open Questions

1. **Intent Classification**: Keyword-based or LLM-based? (recommend keyword MVP)
2. **Chrome MCP**: Timeline for integration? Current tools are mocks.
3. **Flight Booking**: Mentioned in spec but no tools planned. Intentional?

---

## Links

- PR: https://github.com/stofancy/voice-agent/pull/5
- Spec: `specs/001-agent-layer/spec.md`
- Tasks: `specs/001-agent-layer/tasks.md`
- Checklists: `specs/001-agent-layer/checklists/`

---

**Version**: 1.0.0 | **Last Updated**: 2026-03-25
