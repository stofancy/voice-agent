# Data Model: Self-Managed Agent Layer

**Feature**: `001-agent-layer`  
**Created**: 2026-03-25

## Entities

### 1. StreamController

Manages stream output to ensure non-blocking tool calls.

| Field | Type | Description |
|-------|------|-------------|
| `event_queue` | asyncio.Queue | Queue for tool events |
| `tts_stream` | TTSStream | Active TTS stream |
| `is_cancelled` | bool | Cancellation flag |

**State Transitions**:
- IDLE → ACTIVE (on user input)
- ACTIVE → EMITTING (on tool_start)
- EMITTING → IDLE (on stream complete)
- ANY → CANCELLED (on interruption)

### 2. AgentRouter

Routes user requests to appropriate agent based on intent.

| Field | Type | Description |
|-------|------|-------------|
| `agents` | Dict[str, BaseAgent] | Available agents by type |
| `default_agent` | BaseAgent | Fallback agent |
| `classifier` | LLM | Intent classifier |

**Routes**:
- "book", "hotel", "flight" → BookingAgent
- "weather", "what", "how" → QueryAgent
- default → QueryAgent

### 3. BaseAgent

Abstract base for specialized agents.

| Field | Type | Description |
|-------|------|-------------|
| `agent_type` | str | Agent identifier |
| `llm` | BaseLLM | Language model |
| `tools` | List[BaseTool] | Agent tools |
| `conversation_history` | List[Dict] | Turn history |

### 4. BookingAgent

Specialized agent for hotel/flight booking.

**Extends**: BaseAgent  
**Tools**: `search_hotels`, `book_hotel`, `search_flights`, `book_flight`  
**State**: Follows ReAct loop (Thought → Action → Observation)

### 5. QueryAgent

Specialized agent for information queries.

**Extends**: BaseAgent  
**Tools**: `get_weather`, `search_web`, `get_time`  
**State**: Simple request → response

### 6. ConversationContext

Maintains conversation state per session.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | str | Unique session |
| `history` | List[Message] | Full conversation |
| `current_agent` | BaseAgent | Active agent |
| `turn_count` | int | Turn number |

## Events

| Event | Payload | Description |
|-------|---------|-------------|
| `tool_start` | `{tool: str, input: any}` | Tool execution began |
| `tool_progress` | `{tool: str, status: str}` | Intermediate progress |
| `tool_complete` | `{tool: str, output: any}` | Tool finished |
| `tool_error` | `{tool: str, error: str}` | Tool failed |

## Validation Rules

1. **StreamController**: `event_queue` max size = 100 (backpressure)
2. **AgentRouter**: At least 1 agent required
3. **ConversationContext**: `session_id` must be non-empty
4. **Tool execution**: Timeout = 30s default, configurable
