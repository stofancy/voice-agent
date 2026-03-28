# Handover: Browser Booking Automation (003-browser-booking-automation)

**Date**: 2026-03-29
**Branch**: `003-browser-booking-automation`
**Last Commit**: `d05bbd3 feat(agent): add StageToolWrapper and VoiceBookingAgent for NL-based booking`

## 当前状态

### 已完成

- **7 个 Stage Tools** - 浏览器自动化操作（search, select_hotel, navigate_property, select_room, confirm_selection, fill_guest, finalize）
- **StageToolWrapper** - 将 BookingStage 包装为 LangChain StructuredTool
- **VoiceBookingAgent** - LLM-based 预订编排 + NL 解析
- **NL Selection 解析** - "第二个"→index, "贵一点的"→price_desc, "评分最高的"→rating_desc
- **62 个测试全部通过** (39 unit + 10 integration + 13 agent)
- **Spec/Plan/Tasks 文档完整**

### 未完成

1. **VoiceBookingAgent 未集成到 Agent Router**
   - 新建的 `VoiceBookingAgent` 未导出到 `src/server/agent/__init__.py`
   - `src/server/main.py` 仍使用旧的 mock `BookingAgent`

2. **端到端流程未拉通**
   - Stage Tools → VoiceBookingAgent → Agent Router → main.py 链路未完成
   - 缺少真实的 Chrome DevTools MCP 集成测试

3. **Architecture Violation 已修复**
   - 移除了 `select_hotel.py` 中错误的 NL 解析逻辑
   - 确认其他 Stage Tools 无类似问题

## 下一步工作

### Priority 1: 集成 VoiceBookingAgent 到 Agent Router

```python
# 1. 更新 src/server/agent/__init__.py
from .voice_booking_agent import VoiceBookingAgent

# 2. 更新 src/server/agent/router.py
# 添加 voice_booking 类型路由

# 3. 更新 src/server/main.py
# 在 create_booking_agent() 中使用 VoiceBookingAgent
```

### Priority 2: 端到端测试

```python
# 测试流程:
# 1. 启动 Chrome with remote debugging: Chrome --remote-debugging-port=9222
# 2. 用户说: "找东京酒店，4月1号入住，4月5号退房"
# 3. LLM 解析 → 调用 search_hotels
# 4. 显示酒店列表
# 5. 用户说: "选贵一点的"
# 6. LLM 解析 preference → 选择最贵酒店
# 7. 继续 navigate_property → select_room → ... → finalize
```

### Priority 3: 真实浏览器测试

需要：
- Chrome running with `--remote-debugging-port=9222`
- 真实 Booking.com 页面结构

## 关键文件

| 文件 | 说明 |
|------|------|
| `src/server/agent/voice_booking_agent.py` | 新建的 VoiceBookingAgent |
| `src/server/agent/tools/stage_tool_wrapper.py` | Stage Tool 包装器 |
| `src/server/browser/stages/*.py` | 7 个 Stage Tools |
| `src/server/agent/router.py` | Agent 路由（需修改） |
| `src/server/main.py` | 入口（需修改） |

## 测试命令

```bash
# 运行所有测试
.venv/bin/python -m pytest tests/unit/browser/test_stages.py tests/integration/browser/test_booking_flow.py tests/integration/agent/test_voice_booking_agent.py -v

# 预期结果: 62 passed
```

## 架构说明

```
┌─────────────────────────────────────────────────────────────┐
│ BookingAgent (LLM + Tool Orchestration)                    │
│  - Interprets NL: "第二个" → index=2                       │
│  - Calls Stage Tools sequentially                           │
│  - Manages TurnContext state                               │
└─────────────────┬───────────────────────────────────────────┘
                  │ LangChain StructuredTool
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ StageToolWrapper                                            │
│  - Wraps BookingStage as @tool                             │
│  - Converts tool args ↔ context dict                        │
└─────────────────┬───────────────────────────────────────────┘
                  │ async execute()
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage Tools (browser/stages/*.py)                           │
│  - search.py, select_hotel.py, navigate_property.py, etc.  │
│  - Return StageResult with action/data/options             │
└─────────────────────────────────────────────────────────────┘
```

## Git Log

```
d05bbd3 feat(agent): add StageToolWrapper and VoiceBookingAgent for NL-based booking
6ac31a9 feat(browser): add retry mechanism and session pause/resume
abd236b docs(tasks): add implementation task list for browser booking
da1cb92 docs(plan): add Phase 1 planning artifacts for browser booking
d4daeae docs(spec): add Browser Booking Automation specification
```

---

**Handoff 准备完成。下一个 session 可以直接继续 Priority 1 工作。**
