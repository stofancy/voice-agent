# Agent Layer Review Issues

两次Code Review发现的问题汇总。

## 问题列表

### P0 - Critical (影响功能正确性)

| # | 问题 | 位置 | 规格要求 | 状态 |
|---|------|------|----------|------|
| 1 | `tts_factory` undefined | `streaming_synthesis.py:125` | - | ✅ FIXED |
| 2 | Tools不是LangChain兼容格式 | `tools/*.py` | FR-003 | ✅ FIXED |
| 3 | 30s超时机制未实现 | `langchain_agent.py` | FR-007a/b/c | ✅ FIXED |
| 4 | 500ms进度emit机制缺失 | `langchain_agent.py` | FR-010 | ✅ FIXED |

### P1 - High (功能缺陷)

| # | 问题 | 位置 | 规格要求 | 状态 |
|---|------|------|----------|------|
| 5 | Conversation history double-append | `langchain_agent.py:136,144-145` | FR-006a | ✅ FIXED |
| 6 | `stream_rdy_output` 拼写错误 | `factory.py:52` | - | ✅ FIXED |
| 7 | Backpressure threshold未强制执行 | `langchain_agent.py` | FR-009 | ✅ FIXED |
| 8 | event_queue死代码 | `stream_controller.py` | FR-009 | ✅ FIXED |

## 问题详情

### P0-1: tts_factory undefined (FIXED)
```python
# streaming_synthesis.py:125
self.tts = tts_factory.create_stream()  # 已修复为 self._tts.create_stream()
```

### P0-2: Tools格式不正确 (FIXED)
已转换为 `@tool` 装饰器格式：
- query_tool.py: get_weather, web_search, get_time
- hotel_tool.py: search_hotels, book_hotel
- dummy_tool.py: echo_tool

### P0-3: 超时未实现 (FIXED)
FR-007a要求30s超时，已实现：
- 添加 `emit_timeout()` 后台任务
- 添加 `tool_timeout` 配置参数（默认30s）
- 超时后发送 TTS 回退消息

### P0-4: 500ms进度机制缺失 (FIXED)
FR-010要求工具执行中每500ms emit进度消息，已实现：
- 添加 `_emit_periodic_progress()` 后台任务
- 通过 `BackpressureQueue` 协调

### P1-5: Double-append (FIXED)
```python
# 已修复: astream() 现在只在本地创建history时append
using_provided_history = conversation_history is not None
messages = conversation_history if using_provided_history else self._conversation_history
if not using_provided_history:
    messages.append({"role": "user", "content": input_text})
```

### P1-6: 拼写错误 (FIXED)
```python
stream_rdy_output=True  # 拼写错误已修复
```

### P1-7: Backpressure未执行 (FIXED)
FR-009要求队列max_depth=100，已实现：
- 添加 `BackpressureQueue` 类
- 使用 `deque` 实现，`maxlen=100`
- 满时丢弃最老事件并记录警告日志

### P1-8: event_queue死代码 (FIXED)
已移除 `stream_controller.py` 中未使用的 `_event_queue` 和 `astream_events()` 方法

## SDD阶段分析

根据spec-kit流程：
```
SPEC → PLAN → TASKS → CHECKLIST
```

这些问题已全部添加到 tasks.md (T040-T047) 并修复完成。

## 修复总结

**Phase 8: Bug Fixes - 8/8 完成**

| Task | 问题 | 状态 |
|------|------|------|
| T040 | `tts_factory` undefined | ✅ FIXED |
| T041 | LangChain Tools格式 | ✅ FIXED |
| T042 | 30s超时机制 | ✅ FIXED |
| T043 | 500ms进度emit | ✅ FIXED |
| T044 | double-append | ✅ FIXED |
| T045 | `stream_rdy_output` typo | ✅ FIXED |
| T046 | backpressure enforcement | ✅ FIXED |
| T047 | event_queue死代码 | ✅ FIXED |

---
*Created: 2026-03-27*
*Updated: 2026-03-28*
*Status: ALL FIXED*
