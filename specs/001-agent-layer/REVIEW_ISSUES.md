# Agent Layer Review Issues

两次Code Review发现的问题汇总。

## 问题列表

### P0 - Critical (影响功能正确性)

| # | 问题 | 位置 | 规格要求 | 状态 |
|---|------|------|----------|------|
| 1 | `tts_factory` undefined | `streaming_synthesis.py:125` | - | ✅ FIXED |
| 2 | Tools不是LangChain兼容格式 | `tools/*.py` | FR-003 | OPEN |
| 3 | 30s超时机制未实现 | `langchain_agent.py` | FR-007a/b/c | OPEN |
| 4 | 500ms进度emit机制缺失 | `langchain_agent.py` | FR-010 | OPEN |

### P1 - High (功能缺陷)

| # | 问题 | 位置 | 规格要求 | 状态 |
|---|------|------|----------|------|
| 5 | Conversation history double-append | `langchain_agent.py:136,144-145` | FR-006a | ✅ FIXED |
| 6 | `stream_rdy_output` 拼写错误 | `factory.py:52` | - | ✅ FIXED |
| 7 | Backpressure threshold未强制执行 | `streaming_synthesis.py` | FR-009 | OPEN |
| 8 | event_queue死代码 | `stream_controller.py` | FR-009 | ✅ FIXED |

## 问题详情

### P0-1: tts_factory undefined (FIXED)
```python
# streaming_synthesis.py:125
self.tts = tts_factory.create_stream()  # 已修复为 self._tts.create_stream()
```

### P0-2: Tools格式不正确
当前返回的是dict格式：
```python
{"name": "get_weather", "description": "...", "function": async def...}
```
LangChain需要的是 `from langchain_core.tools import tool` 装饰的Function

### P0-3: 超时未实现
FR-007a要求30s超时，但代码中无任何timeout处理

### P0-4: 500ms进度机制缺失
FR-010要求工具执行中每500ms emit进度消息，当前只在tool_start时emit一次

### P1-5: Double-append (FIXED)
```python
# 已修复: astream() 现在只在本地创建history时append，不在调用者传入时append
using_provided_history = conversation_history is not None
messages = conversation_history if using_provided_history else self._conversation_history
if not using_provided_history:
    messages.append({"role": "user", "content": input_text})
```

### P1-6: 拼写错误 (FIXED)
```python
stream_rdy_output=True  # 拼写错误已修复
```

### P1-7: Backpressure未执行
FR-009要求队列max_depth=100，但无enforce机制

### P1-8: event_queue死代码 (FIXED)
已移除 `stream_controller.py` 中未使用的 `_event_queue` 和 `astream_events()` 方法

## SDD阶段分析

根据spec-kit流程：
```
SPEC → PLAN → TASKS → CHECKLIST
```

这些问题属于 **TASKS 阶段**：
- spec.md 已定义功能需求（FR-006~010）
- 已添加为 T040-T047 到 tasks.md
- 4个简单问题已修复

## 修复优先级

1. **P0-1**: ✅ tts_factory undefined - 已修复
2. **P0-2**: Tools格式 - 需较大改动
3. **P0-3**: 超时机制 - 需设计实现
4. **P0-4**: 500ms进度 - 需新增定时器机制
5. **P1-5~8**: ✅ 已全部修复

---
*Created: 2026-03-27*
*Updated: 2026-03-28*
