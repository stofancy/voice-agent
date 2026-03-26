# Feature Specification: Self-Managed Agent Layer

**Feature Branch**: `001-agent-layer`  
**Created**: 2026-03-24  
**Status**: Draft  
**Input**: User description: "Replace OpenClaw agent dependency with LangChain agent for full streaming control during tool calls. Support multi-agent routing (booking, query). Emit intermediate progress during tool execution to prevent TTS silence."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Non-Blocking Tool Calls (Priority: P1)

As a user, I want to hear continuous responses during tool execution so I don't experience frustrating silence.

**Why this priority**: Core problem - OpenClaw blocks stream during tool calls, breaking TTS experience

**Independent Test**: Can be fully tested by triggering a tool call and verifying TTS continues without >500ms silence

**Acceptance Scenarios**:

1. **Given** agent is processing a request, **When** a tool call takes >500ms, **Then** intermediate status is spoken via TTS (e.g., "processing your booking...")

2. **Given** tool call completes, **When** response is received, **Then** stream resumes immediately with result

3. **Given** tool call fails, **When** error occurs, **Then** error is spoken and recovery suggestion offered

---

### User Story 2 - Voice Booking Flow (Priority: P1)

As a user, I want to book hotels and flights via voice so I can complete transactions hands-free.

**Why this priority**: Demonstrates real-world use case requiring multi-step tool interactions

**Independent Test**: Can be tested by saying "book a hotel for tomorrow" and verifying booking flow completes with confirmation

**Acceptance Scenarios**:

1. **Given** user says "I want to book a hotel", **When** booking agent receives intent, **Then** agent asks clarifying questions (dates, location) via TTS

2. **Given** user provides booking details, **When** agent calls booking tool, **Then** TTS streams progress without blocking

3. **Given** booking completes, **When** confirmation is ready, **Then** agent speaks confirmation details and booking reference

---

### User Story 3 - Multi-Agent Routing (Priority: P2)

As a user, I want different tasks routed to specialized agents so each task gets optimal handling.

**Why this priority**: Enables extensibility beyond single booking flow

**Independent Test**: Can be tested by sending different intents (booking vs query) and verifying correct agent handles each

**Acceptance Scenarios**:

1. **Given** user says "what's the weather in Beijing?", **When** query agent receives intent, **Then** weather tool is called and result spoken

2. **Given** user says "book a flight to Shanghai", **When** booking agent receives intent, **Then** flight booking flow initiates

---

### User Story 4 - Stream Control During Interruption (Priority: P1)

As a user, I want to interrupt the agent at any time so I can correct or change my request.

**Why this priority**: Essential for voice UX - users must feel in control

**Independent Test**: Can be tested by speaking during agent response and verifying new input is processed

**Acceptance Scenarios**:

1. **Given** agent is speaking, **When** user interrupts mid-sentence, **Then** current stream stops and new input is processed

2. **Given** tool is executing, **When** user interrupts, **Then** tool execution is cancelled and new request processed

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST replace OpenClaw agent with LangChain agent implementation
- **FR-002**: Tool calls MUST NOT block LLM stream - intermediate progress MUST be emitted within 200ms
- **FR-003**: System MUST emit structured events: `tool_start`, `tool_progress`, `tool_complete`, `tool_error`
- **FR-004**: System MUST support at least 2 concurrent specialized agents (booking, query)
- **FR-005**: System MUST route requests to appropriate agent based on intent classification
- **FR-006**: Agent state MUST be maintained across turns in a conversation
- **FR-007**: User interruption MUST cancel in-flight tool calls and reset stream
- **FR-008**: WebSocket protocol MUST remain backward compatible with existing frontend

### Key Entities

- **AgentRouter**: Routes user requests to appropriate agent based on intent classification
- **BookingAgent**: Specialized agent for hotel/flight booking with tool definitions
- **QueryAgent**: Specialized agent for information queries (weather, facts, etc.)
- **StreamController**: Manages stream output to ensure non-blocking tool calls
- **ConversationContext**: Maintains conversation history and state per session

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tool calls do not cause >200ms gap in stream output
- **SC-002**: TTS continues speaking during tool execution (no silence >500ms)
- **SC-003**: Multiple agents can be instantiated and queried concurrently
- **SC-004**: Existing WebSocket protocol remains compatible (no breaking changes to frontend)
- **SC-005**: User interruption is processed within 300ms

## Assumptions

- LLM provider remains OpenAI-compatible API (configurable)
- STT and TTS infrastructure remains unchanged
- LangChain Agents provides agent scaffolding with custom stream handling
- WebSocket message types can be extended but not removed
- Session state is ephemeral (no persistence across server restarts)

## Implementation Details

### Intent Classification (FR-005)

Intent classification uses **keyword-based routing**:

| Keyword Pattern | Routes To |
|----------------|-----------|
| `book`, `hotel`, `flight`, `reserve`, `room`, `booking` | BookingAgent |
| `weather`, `search`, `find`, `what`, `who`, `when`, `where`, `how`, `time`, `information`, `look up`, `check` | QueryAgent |
| No match | Default: BookingAgent (fallback) |

**Note**: Keyword scoring sums matches per category. Higher score wins. Ties broken by category priority (booking > query).

### Routing Failure Behavior (Edge Case)

When no agent matches:
1. If `booking_agent` is configured → route to BookingAgent (default fallback)
2. Else if `query_agent` is configured → route to QueryAgent
3. Else → raise `ValueError("No agents configured for routing")`

### Tool Execution

**Timeouts**:
- Default tool timeout: 30 seconds
- Tools that exceed timeout emit `tool_error` event and return timeout message

**Retry**: No automatic retry. Tool failure emits `tool_error` event; user can re-request.

### LangChain Agent Limitations

- `astream_events()` provides non-blocking token emission
- Tool execution within LangChain Agent may block LLM stream if tool is synchronous
- Solution: Use async tools where possible; StreamController intercepts and emits without blocking
- Stream gap target (<200ms) achievable with async tool implementations

### WebSocket Event Payload (FR-003)

Events emitted during tool lifecycle:

```json
{
  "type": "tool_start|tool_progress|tool_complete|tool_error",
  "tool_name": "string",
  "data": {} | "string",
  "timestamp": "ISO8601"
}
```

### Interruption Behavior (FR-007)

On user interruption:
1. `TurnContext.cancelled` Event is set
2. StreamController checks `is_cancelled()` before emitting
3. TTS receives fallback: "Sorry, let me start over."
4. Stream terminates gracefully

### Progress Messages (FR-002)

During long tool calls, TTS speaks progress messages:

| Tool Type | Progress Message |
|-----------|-----------------|
| `search_hotels` | "Searching for hotels..." |
| `book_hotel` | "Processing your booking..." |
| `get_weather` | "Checking the weather..." |
| Default | "One moment please..." |
