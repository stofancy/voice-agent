# OpenClaw Concepts Quick Reference

## Core Concepts

### Agents
- Autonomous entities that reason, remember, and take actions
- Can be conversational (chat-based) or task-oriented
- Powered by LLMs with access to memory and tools
- **Docs**: `https://docs.openclaw.ai/concepts/agents.md`

### Memory
- Persistent storage of conversation history and learned information
- Multiple backends: in-memory, database, vector store
- Two types: **short-term** (conversation) and **long-term** (knowledge)
- **Docs**: `https://docs.openclaw.ai/concepts/memory.md`

### Tools
- Functions that agents can call to take action
- Include built-ins (web search, calculation) and custom tools
- Tool schema defines inputs, outputs, and execution flow
- **Docs**: `https://docs.openclaw.ai/concepts/tools.md`

### Gateway
- Central server for agent deployment and orchestration
- Manages WebSocket connections with multiple clients
- Routes messages, memory, and tool calls
- **Docs**: `https://docs.openclaw.ai/gateway/overview.md`

### Extensions (Plugins)
- Custom plugins that extend OpenClaw functionality
- Can add memory backends, tools, or UI components
- Follow standard plugin lifecycle and schema
- **Docs**: `https://docs.openclaw.ai/extensions/overview.md`

## Architecture Layers

```
┌─────────────────────────────────────┐
│         Client (Browser/App)        │
└─────────────────┬───────────────────┘
                  │ WebSocket
┌─────────────────▼───────────────────┐
│       OpenClaw Gateway              │
│  (Message routing, memory mgmt)     │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┼─────────┐
        │         │         │
        ▼         ▼         ▼
    ┌────┐   ┌────────┐  ┌─────┐
    │LLM │   │Memory  │  │Tools│
    │API │   │Backend │  │Exec │
    └────┘   └────────┘  └─────┘
```

## Common Development Tasks

### 1. Create a Custom Memory Backend
```python
# Implement the MemoryBackend interface
class CustomMemoryBackend(MemoryBackend):
    async def store(self, key: str, value: Any) -> None:
        # Store in your backend
        pass
    
    async def retrieve(self, key: str) -> Any:
        # Retrieve from your backend
        pass
    
    async def list_keys(self) -> List[str]:
        # List all stored keys
        pass
```
**Reference**: `https://docs.openclaw.ai/memory/custom-backends.md`

### 2. Create a Custom Tool
```python
# Define the tool schema and handler
class MyTool(Tool):
    name = "my_tool"
    description = "What this tool does"
    parameters = {
        "param1": {"type": "string", "description": "..."},
    }
    
    async def execute(self, **kwargs) -> str:
        # Implement the tool
        return result
```
**Reference**: `https://docs.openclaw.ai/tools/custom-tools.md`

### 3. Build an Extension
```python
# Register with OpenClaw plugin system
class MyExtension(Extension):
    name = "my-extension"
    version = "1.0.0"
    
    def on_load(self):
        # Register tools, memory backends, etc.
        pass
```
**Reference**: `https://docs.openclaw.ai/extensions/creating-plugins.md`

### 4. Deploy Gateway Instance
```bash
# Configuration via environment or config file
OPENCLAW_PORT=8765
OPENCLAW_MASTER_KEY=your-admin-key
OPENCLAW_EXTENSIONS_PATH=/path/to/plugins
```
**Reference**: `https://docs.openclaw.ai/gateway/deployment.md`

## When to Check Docs

| Situation | Check This Docs Page |
|-----------|---------------------|
| "How does memory work?" | `/concepts/memory.md` |
| "I'm building a tool" | `/tools/custom-tools.md` |
| "How do I add a plugin?" | `/extensions/creating-plugins.md` |
| "Memory isn't persisting" | `/troubleshooting/memory-issues.md` |
| "Tool execution is failing" | `/troubleshooting/tool-errors.md` |
| "How's the gateway protocol?" | `/api/websocket-protocol.md` |
| "Can I use PostgreSQL?" | `/integration/databases.md` |

## Key Files to Know

- `openclaw.json` - Gateway configuration file
- `plugin.yaml` - Extension metadata
- `.env` - Environment variables for deployment
- `memory/` - Memory backend implementations
- `tools/` - Tool definitions and handlers

## Useful Links

- **Official Docs**: https://docs.openclaw.ai/
- **GitHub**: https://github.com/openclaw/openclaw
- **Community Issues**: https://github.com/openclaw/openclaw/issues
- **Markdown URLs**: Append `.md` to any docs page for markdown format
