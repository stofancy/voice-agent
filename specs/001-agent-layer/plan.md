# Implementation Plan: Self-Managed Agent Layer

**Branch**: `001-agent-layer` | **Date**: 2026-03-24 | **Spec**: [link](./spec.md)
**Input**: Feature specification from `/specs/001-agent-layer/spec.md`

## Summary

Replace OpenClaw agent dependency with LangChain Agents to achieve full streaming control during tool calls. Current architecture blocks during tool execution; target architecture maintains continuous stream with intermediate tool progress updates. LangChain Agents chosen for rapid prototyping while maintaining control over streaming behavior.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: langchain, langchain-openai, langchain-agents  
**Storage**: N/A (stateless per session)  
**Testing**: pytest  
**Target Platform**: Linux server  
**Project Type**: WebSocket voice service  
**Performance Goals**: <200ms stream gap during tool calls, <500ms STT latency  
**Constraints**: WebSocket protocol backward compatible, memory <200MB baseline  
**Scale/Scope**: Single session, multiple concurrent sessions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Single Responsibility**: New agent layer is separate module (`src/server/agent/`)
- [x] **II. Test-First**: LangChain prototyping phase includes streaming behavior tests
- [x] **III. Streaming-First**: Architecture ensures non-blocking tool calls via StreamController
- [x] **IV. WebSocket State Machine**: Agent events integrate with existing state machine
- [x] **V. Observability**: Structured events for tool lifecycle (tool_start, tool_complete, etc.)

## Project Structure

### Documentation (this feature)

```text
specs/001-agent-layer/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # LangChain streaming research (Phase 0)
├── data-model.md        # Agent, StreamController entities (Phase 1)
├── quickstart.md        # Local testing guide (Phase 1)
└── tasks.md             # Implementation tasks (Phase 2)
```

### Source Code

```text
src/server/
├── llm/
│   ├── base.py                 # Unchanged
│   ├── openai_llm.py           # Unchanged (still used for LLM calls)
│   └── factory.py              # Unchanged
├── agent/                      # NEW - self-managed agent layer
│   ├── __init__.py
│   ├── base.py                 # Base agent interface
│   ├── router.py               # Intent routing to agents
│   ├── booking_agent.py        # Booking-specific agent
│   ├── query_agent.py          # Query-specific agent
│   └── stream_controller.py    # Manages non-blocking tool streams
├── tts/
├── stt/
└── ...

tests/
├── unit/
│   └── agent/                  # NEW
│       ├── test_router.py
│       ├── test_booking_agent.py
│       └── test_stream_controller.py
└── ...
```

**Structure Decision**: Single project structure chosen. Agent layer (`src/server/agent/`) is new module alongside existing llm/, tts/, stt/ modules. Backward compatible with existing architecture.

## Technical Approach

### Architecture Change

```
CURRENT:
Browser → STT → OpenAI LLM → [TOOL_CALL blocks] → TTS → Browser
                     ↑
              OpenClaw Gateway

TARGET:
Browser → STT → LangChain Agent → StreamController → TTS → Browser
                     ↓
              Tools (booking, query...)
              Non-blocking via async tool events
```

### Key Design Decisions

1. **LangChain Agent as orchestration layer**: Wraps OpenAI-compatible LLM, adds tool definitions, manages ReAct loop
2. **StreamController**: Custom component that intercepts agent steps and emits streaming events without blocking
3. **Event-based communication**: Agent emits `tool_start`, `tool_progress`, `tool_complete`, `tool_error` events; StreamController handles these to maintain TTS stream
4. **Backward compatible**: Existing WebSocket message types extended, not removed

### LangChain Agent Integration

```python
# Pseudocode for stream-aware agent
class StreamingAgent:
    def __init__(self, llm, tools, stream_controller):
        self.agent = create_langchain_agent(llm, tools)
        self.stream_controller = stream_controller
    
    async def astream(self, input_text):
        async for event in self.agent.astream_events(input_text):
            if event.type == "tool":
                await self.stream_controller.emit_tool_event(event)
            yield event.data  # Continue stream without blocking
```

## Phase Dependencies

- **Research (Phase 0)**: Evaluate LangChain agent streaming capabilities ✅ Can start immediately
- **Design (Phase 1)**: StreamController design, event schema ✅ Depends on Phase 0
- **Foundational (Phase 2)**: Agent base class, router, basic tools ✅ Depends on Phase 1
- **User Story 1 (Phase 3)**: Non-blocking tool calls with working stream ✅ Depends on Phase 2
- **User Story 2 (Phase 4)**: Booking agent ✅ Depends on Phase 3
- **User Story 3 (Phase 5)**: Multi-agent routing ✅ Depends on Phase 4
- **User Story 4 (Phase 6)**: Interruption handling ✅ Depends on Phase 5
- **Polish (Phase 7)**: Integration testing, performance validation ✅ Depends on Phase 6

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None yet | | |
