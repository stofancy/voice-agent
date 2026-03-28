# Research: Self-Managed Agent Layer

**Date**: 2026-03-24  
**Feature**: Replace OpenClaw with LangChain Agents for streaming control

## Research Questions

1. How to stream tool events from LangChain Agent without blocking?
2. What's the best pattern for non-blocking tool execution?

---

## Finding 1: LangChain Agent Streaming API

**Decision**: Use `astream_events()` method for streaming tool execution

**Rationale**: LangChain agents built on LangGraph support `astream_events()` which yields events during agent execution. Events include `on_tool_start`, `on_tool_end`, etc.

**Evidence**: LangChain docs confirm agents built on LangGraph support streaming events including tool lifecycle.

**Alternatives considered**:
- `ainvoke()` - blocks until complete, not suitable
- `stream()` - streams LLM tokens but not tool events

---

## Finding 2: Tool Callback Handler Pattern

**Decision**: Use LangChain's callback handler to intercept tool events

**Rationale**: LangChain supports `BaseCallbackHandler` which receives `on_tool_start`, `on_tool_end`, etc. callbacks. This allows emitting TTS text during tool execution.

**Code pattern**:
```python
from langchain_core.callbacks import BaseCallbackHandler

class StreamCallback(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, **kwargs):
        # Emit "processing..." to TTS immediately
        self.stream_controller.emit_progress("processing...")
    
    def on_tool_end(self, output, **kwargs):
        # Tool complete - continue with result
        pass
```

**Alternatives considered**:
- Custom ReAct loop - too much boilerplate
- LangGraph interrupts - more complex than needed

---

## Finding 3: Non-Blocking Tool Execution

**Decision**: Use async tool execution with immediate callback dispatch

**Rationale**: Tools run in thread pool via LangChain's executor. Callbacks fire immediately when tool starts/ends, allowing TTS stream to continue.

**Key insight**: Tool execution is fire-and-forget from LLM perspective. The callback handler can emit TTS text while tool runs in background.

---

## Finding 4: Integration with Existing Architecture

**Decision**: StreamController wraps LangChain callback handler

**Rationale**: Existing `StreamingSynthesis` class already handles LLM→TTS flow. StreamController adds tool event handling on top.

**Architecture**:
```
StreamingSynthesis (existing)
    ↓
StreamController (NEW - LangChain callback handler)
    ↓
LangChain Agent
    ↓
Tools (booking, query)
```

---

## Summary

| Question | Decision | Confidence |
|----------|----------|-------------|
| Streaming API | `astream_events()` | High |
| Tool interception | `BaseCallbackHandler` | High |
| Non-blocking pattern | Async callbacks | High |
| Integration approach | StreamController wrapper | High |

## Next Steps

1. Implement `BaseCallbackHandler` in `stream_controller.py`
2. Test `astream_events()` with sample agent
3. Verify callback fires before tool completes
