# Quickstart: Self-Managed Agent Layer

**Feature**: `001-agent-layer`  
**Created**: 2026-03-25

## Prerequisites

- Python 3.10+
- `pip install langchain langchain-openai`
- Voice Agent running (STT + TTS)

## Local Testing

### 1. Start Voice Agent

```bash
cd /home/ztmdsbt/workspaces/voice-agent
source .venv/bin/activate
python -m src.server.main
```

### 2. Connect via WebSocket

```javascript
// Connect to ws://localhost:8765/ws
const ws = new WebSocket('ws://localhost:8765/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'start_listening' }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log('Event:', msg.type, msg);
};
```

### 3. Test Non-Blocking Tool Call

```bash
# Send a query that triggers a tool call
# e.g., "What's the weather in Beijing?"
```

**Expected behavior**:
1. TTS speaks: "Let me check that for you..."
2. Tool executes (no silence)
3. TTS speaks result immediately after tool completes

### 4. Verify Stream Continuity

Open browser DevTools Network tab:
- Look for `audio_chunk` events
- Gap between chunks should be <500ms during tool calls

## Test Scenarios

### Scenario 1: Simple Query (No Tool)

**Input**: "Hello, how are you?"  
**Expected**: Direct response, no tool call

### Scenario 2: Tool Call with Progress

**Input**: "What's the weather in Beijing?"  
**Expected**: 
1. "Let me check..." (immediate)
2. Tool executes
3. "It's sunny and 25°C"

### Scenario 3: Booking Flow

**Input**: "I want to book a hotel for tomorrow"  
**Expected**:
1. Questions for details (date, location)
2. Tool calls for search
3. Booking confirmation

### Scenario 4: Interruption

**Input**: Start a query, then speak again mid-response  
**Expected**: New input cancels current stream

## Debug Commands

```bash
# Enable verbose logging
LOG_LEVEL=DEBUG python -m src.server.main

# Run unit tests
.venv/bin/python -m pytest tests/unit/agent/ -v
```

## Common Issues

| Issue | Solution |
|-------|----------|
| TTS silence >500ms | Check StreamController callback |
| Tool not called | Verify intent classification |
| Interruption not working | Check TurnContext cancellation |
