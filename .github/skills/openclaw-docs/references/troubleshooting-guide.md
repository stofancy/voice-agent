# OpenClaw Troubleshooting Guide

Common issues, solutions, and how to debug problems with OpenClaw agents.

## Memory Issues

### Problem: Agent doesn't remember previous conversations

**Symptoms**:
- Agent forgets context between messages
- Memory queries return empty/null
- "I don't recall" responses even after you just told it something

**Debugging Steps**:
1. Check memory backend is initialized
   ```python
   if not agent.memory:
       logger.error("Memory backend not initialized")
   ```

2. Verify memory store/retrieve works
   ```python
   await agent.memory.store("test_key", {"test": "value"})
   result = await agent.memory.retrieve("test_key")
   assert result == {"test": "value"}
   ```

3. Check TTL (time-to-live) settings
   ```python
   # Memory might be expiring too quickly
   # Increase TTL in your backend configuration
   ttl_seconds = 86400 * 30  # 30 days
   ```

4. Verify agent_id consistency
   ```python
   # Each agent must use same ID for memory persistence
   agent_id = "user-123"  # Must be consistent
   await memory.store(agent_id, "memories", data)
   ```

**Solutions**:
- Reference: `https://docs.openclaw.ai/troubleshooting/memory-issues.md`
- Check [memory/custom-backends.md](https://docs.openclaw.ai/memory/custom-backends.md)
- Implement debug logging in memory backend

---

## Tool Execution Issues

### Problem: Agent can't call tools or tools fail silently

**Symptoms**:
- Tool returns error without description
- Agent says "I don't have access to that"
- Tool execution timeout

**Debugging Steps**:
1. Verify tool is registered
   ```python
   assert "my_tool" in agent.tools
   assert agent.tools["my_tool"].name == "my_tool"
   ```

2. Check tool schema is valid
   ```python
   tool = agent.tools["my_tool"]
   assert hasattr(tool, "parameters")
   assert hasattr(tool, "execute")
   ```

3. Test tool directly
   ```python
   result = await tool.execute(param1="value")
   print(f"Tool result: {result}")
   ```

4. Check error logs
   ```python
   # Enable debug logging
   logger.enable("openclaw")
   logger.level("DEBUG")
   ```

**Solutions**:
- Reference: `https://docs.openclaw.ai/troubleshooting/tool-errors.md`
- Ensure tool methods are `async`
- Add proper error handling in execute()
- Return dict with both success and error paths

---

## Connection Issues

### Problem: Gateway/Agent connection fails

**Symptoms**:
- WebSocket connection refused
- "Connection timeout" errors
- Agent unreachable from gateway

**Debugging Steps**:
1. Check gateway is running
   ```bash
   curl http://localhost:8765/health
   # Should return 200 OK
   ```

2. Verify port is correct
   ```python
   # Check environment configuration
   OPENCLAW_PORT=8765  # Default
   ```

3. Check firewall/network
   ```bash
   netstat -an | grep 8765
   # Should see LISTEN
   ```

4. Enable connection logging
   ```python
   logger.add("gateway.log", level="DEBUG")
   ```

**Solutions**:
- Reference: `https://docs.openclaw.ai/gateway/deployment.md`
- Restart gateway service
- Check system logs: `journalctl -u openclaw-gateway -f`
- Verify API keys and authentication tokens

---

## Performance Issues

### Problem: Agent responses are very slow

**Symptoms**:
- Response time > 10 seconds
- Memory queries are slow
- Tool execution hangs

**Debugging Steps**:
1. Profile response time
   ```python
   import time
   start = time.time()
   response = await agent.process("Hello")
   elapsed = time.time() - start
   logger.info(f"Response time: {elapsed:.2f}s")
   ```

2. Check database query performance
   ```python
   # Add timing to memory operations
   start = time.time()
   data = await memory.retrieve(key)
   logger.debug(f"Memory retrieve took {time.time() - start:.3f}s")
   ```

3. Test LLM API latency
   ```python
   # Check if slow response is from LLM or application
   response = await client.chat.completions.create(
       model="gpt-4",
       messages=[{"role": "user", "content": "Hi"}]
   )
   ```

**Solutions**:
- Add database indexes to memory backend
- Cache frequently accessed data
- Use smaller LLM models for faster inference
- Optimize tool execution (parallel calls when possible)

---

## Extension/Plugin Issues

### Problem: Custom extension won't load

**Symptoms**:
- Plugin doesn't appear in agent tools
- Import errors when loading plugin
- Plugin load fails silently

**Debugging Steps**:
1. Verify plugin structure
   ```
   my-plugin/
   ├── __init__.py
   ├── plugin.yaml
   ├── tool.py
   └── setup.py
   ```

2. Check plugin.yaml syntax
   ```yaml
   name: my-plugin
   version: 1.0.0
   type: tool  # or: memory, ui
   entrypoint: my_plugin:MyTool
   ```

3. Test plugin import
   ```python
   from my_plugin import MyTool
   tool = MyTool()
   assert hasattr(tool, "execute")
   ```

4. Check plugin path
   ```bash
   export OPENCLAW_EXTENSIONS_PATH=/path/to/plugins
   # Agent will search this directory
   ```

**Solutions**:
- Reference: `https://docs.openclaw.ai/extensions/creating-plugins.md`
- Verify Python import path
- Test plugin in isolation first
- Check extension discovery logs

---

## Authentication Issues

### Problem: Gateway rejects authentication

**Symptoms**:
- "Invalid API key" errors
- Rate limiting when connecting
- "Access denied" responses

**Debugging Steps**:
1. Verify API key format
   ```python
   api_key = os.getenv("OPENCLAW_MASTER_KEY")
   assert api_key is not None, "API key not set"
   assert len(api_key) > 10, "API key seems too short"
   ```

2. Check token validity
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://localhost:8765/auth/verify
   ```

3. Check rate limits
   ```python
   # Look for rate limit headers
   if "X-RateLimit-Remaining" in response.headers:
       logger.warning(f"Rate limit: {response.headers['X-RateLimit-Remaining']}")
   ```

**Solutions**:
- Regenerate API key: `python scripts/generate_master_key.py`
- Check token hasn't expired
- Increase rate limits if needed
- Use connection pooling to reduce overhead

---

## Quick Debugging Checklist

- [ ] Logs show no errors? Check log level is set to DEBUG
- [ ] Tool works in isolation? Test directly without agent
- [ ] Memory backend responds? Check connectivity and TTL
- [ ] Network connectivity? Ping gateway service
- [ ] Configuration correct? Verify all env vars are set
- [ ] Dependencies installed? Run `pip install -e ".[dev]"`
- [ ] Service restarted? Try restarting gateway after changes
- [ ] Permissions correct? Check file/directory permissions

---

## Getting Help

If you're stuck:

1. **Search the docs**: `https://docs.openclaw.ai/troubleshooting/`
2. **Check GitHub issues**: `https://github.com/openclaw/openclaw/issues`
3. **Enable debug logging**: `logger.level("DEBUG")`
4. **Reproduce in isolation**: Test component independently
5. **Ask in community**: Include logs and minimal reproduction case

---

## Useful Debug Tools

### Log Aggregation
```bash
# Watch all logs in real-time
docker compose logs -f

# Export logs for analysis
docker compose logs > debug.log
```

### Direct Component Testing
```python
# Test memory backend directly
from src.memory import RedisMemoryBackend

memory = RedisMemoryBackend()
await memory.connect()
await memory.store("test", "key", {"data": "value"})
result = await memory.retrieve("test", "key")
print(result)
```

### Tool Testing
```python
# Test tool independently
from my_tool import MyTool

tool = MyTool()
result = await tool.execute(param="test")
print(result)
```

### Agent Testing
```python
# Test agent in isolation
from openclaw import Agent

agent = Agent(memory_backend=memory, tools=[tool1, tool2])
response = await agent.process("What's the weather?")
print(response)
```
