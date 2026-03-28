# Agent Interface Contracts

**Feature**: `001-agent-layer`

## Interface: BaseAgent

```python
class BaseAgent(ABC):
    @property
    def agent_type(self) -> str: ...
    
    async def astream(self, input_text: str) -> AsyncGenerator[AgentEvent, None]: ...
    
    async def ainvoke(self, input_text: str) -> AgentResult: ...
```

## Interface: StreamController

```python
class StreamController(ABC):
    def emit_progress(self, text: str) -> None: ...
    def emit_tool_start(self, tool_name: str, input_data: Any) -> None: ...
    def emit_tool_complete(self, tool_name: str, output: Any) -> None: ...
    def emit_tool_error(self, tool_name: str, error: str) -> None: ...
    async def astream_events(self, input_text: str) -> AsyncGenerator[Event, None]: ...
```

## Interface: Tool

```python
class BaseTool(ABC):
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    
    async def ainvoke(self, input_data: Dict) -> ToolResult: ...
```

## WebSocket Events (Extended)

| Event | Direction | Payload |
|-------|-----------|---------|
| `agent_start` | Server→Client | `{agent_type: str}` |
| `tool_start` | Server→Client | `{tool: str}` |
| `tool_progress` | Server→Client | `{tool: str, status: str}` |
| `tool_complete` | Server→Client | `{tool: str, result: any}` |
| `tool_error` | Server→Client | `{tool: str, error: str}` |
