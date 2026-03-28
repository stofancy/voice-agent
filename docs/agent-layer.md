# Agent Layer Architecture

**Feature Branch**: `001-agent-layer`  
**Status**: Implemented

## Overview

The Agent Layer replaces OpenClaw dependency with LangChain Agents to achieve full streaming control during tool calls. This allows the system to emit intermediate progress updates during long-running tool executions, preventing TTS silence.

## Architecture

```
Browser → STT → VoiceTurn → [Agent/StreamingSynthesis] → TTS → Browser
                         ↓
                  ┌──────┴──────┐
                  │             │
            LangChainAgent  StreamingSynthesis
                  ↓
            StreamController
                  ↓
            Tools (hotel, query, dummy)
```

## Key Components

### VoiceTurn (`src/server/voice_turn.py`)

Orchestrates the complete voice turn. Accepts optional `agent` parameter for LangChain agent mode.

- Without agent: Uses `StreamingSynthesis` with raw LLM
- With agent: Uses `AgentStreamingSynthesis` with LangChain agent

### AgentStreamingSynthesis (`src/server/agent/agent_streaming_synthesis.py`)

Handles LangChain agent event streaming and TTS audio generation in parallel.

- Intercepts `StreamChunkEvent` for TTS feeding
- Handles `ToolStartEvent`/`ToolCompleteEvent` for progress reporting
- Non-blocking via async loops

### StreamController (`src/server/agent/stream_controller.py`)

LangChain callback handler for streaming tool events.

- Intercepts `on_llm_start`, `on_llm_new_token`, `on_tool_start`, `on_tool_end`
- Emits progress to TTS without blocking
- Supports cancellation via `is_cancelled` flag

### BaseAgent (`src/server/agent/base.py`)

Abstract base class for all agents.

```python
class BaseAgent(ABC):
    @property
    def agent_type(self) -> str: ...
    
    async def astream(self, input_text, conversation_history) -> AsyncGenerator[AgentEvent]: ...
    
    async def ainvoke(self, input_text, conversation_history) -> str: ...
```

### Agents

- **BookingAgent**: Hotel booking with `search_hotels` and `book_hotel` tools
- **QueryAgent**: Information queries with `get_weather`, `web_search`, `get_time` tools
- **LangChainAgent**: Generic LangChain wrapper using `astream_events()`

### Router (`src/server/agent/router.py`)

Keyword-based intent classifier routing requests to appropriate agent.

```python
class AgentRouter:
    def classify_intent(self, text) -> Tuple[str, float]: ...
    def route(self, text) -> BaseAgent: ...
```

## Events

All agent events inherit from `AgentEvent`:

- `StreamChunkEvent`: LLM text token
- `ToolStartEvent`: Tool execution started
- `ToolProgressEvent`: Tool execution progress
- `ToolCompleteEvent`: Tool execution completed
- `ToolErrorEvent`: Tool execution failed
- `AgentStartEvent`: Agent started
- `AgentCompleteEvent`: Agent finished

## Tool Registry

| Tool | File | Purpose |
|------|------|---------|
| echo | `tools/dummy_tool.py` | Testing |
| search_hotels | `tools/hotel_tool.py` | Hotel search |
| book_hotel | `tools/hotel_tool.py` | Hotel booking |
| get_weather | `tools/query_tool.py` | Weather info |
| web_search | `tools/query_tool.py` | Web search |
| get_time | `tools/query_tool.py` | Time lookup |

## Cancellation

Interruption handling uses `TurnContext.cancelled` asyncio.Event:

1. User interrupts → `turn_context.cancel()` called
2. `is_cancelled()` returns True
3. StreamController checks flag before emitting
4. TTS fallback "Sorry, let me start over" sent

## Dependencies

```
src/server/agent/
├── __init__.py
├── base.py
├── events.py
├── factory.py
├── langchain_agent.py
├── llm_factory.py
├── router.py
├── stream_controller.py
├── agent_streaming_synthesis.py
├── booking_agent.py
├── query_agent.py
└── tools/
    ├── __init__.py
    ├── dummy_tool.py
    ├── hotel_tool.py
    └── query_tool.py
```

## Usage Example

```python
from src.server.agent import create_booking_agent, AgentRouter

# Create agent
booking_agent = create_booking_agent(llm)

# Use in VoiceTurn
turn = VoiceTurn(
    stt=stt,
    llm=llm,
    tts=tts,
    websocket=ws,
    config=config,
    turn_context=turn_context,
    agent=booking_agent,
)

# Or route with router
router = AgentRouter(
    booking_agent=booking_agent,
    query_agent=query_agent,
)
agent = router.route("Book a hotel for tomorrow")
```