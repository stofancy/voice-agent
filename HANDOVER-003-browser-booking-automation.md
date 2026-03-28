# Handover: Browser Booking Automation (003-browser-booking-automation)

**Date**: 2026-03-29
**Branch**: `003-browser-booking-automation`
**Last Commit**: `b486ef4 docs: add handover documentation for next session`

## 重大架构变更 ⚠️

### 决策：使用 agent-browser (Vercel) 替代 Chrome DevTools MCP

**原因**：
- Chrome DevTools MCP 需要用户本地安装 Chrome 并配置 remote debugging
- agent-browser 提供更简单的 API 和更好的抽象
- Vercel 平台集成更方便

**影响**：
- `src/server/browser/` 下的 BrowserController 实现需要重构
- Stage Tools 的 `browser_controller` 接口保持不变
- 不再需要 `chrome-devtools-mcp` 依赖

## 当前状态

### 已完成

- **7 个 Stage Tools** - 浏览器自动化操作（search, select_hotel, navigate_property, select_room, confirm_selection, fill_guest, finalize）
- **StageToolWrapper** - 将 BookingStage 包装为 LangChain StructuredTool
- **VoiceBookingAgent** - LLM-based 预订编排 + NL 解析
- **NL Selection 解析** - "第二个"→index, "贵一点的"→price_desc, "评分最高的"→rating_desc
- **62 个测试全部通过** (39 unit + 10 integration + 13 agent)
- **Spec/Plan/Tasks 文档完整**

### 未完成

1. **agent-browser 集成**
   - 需要调研 agent-browser Vercel SDK
   - 替换 `BrowserController` 的 Chrome DevTools 实现

2. **VoiceBookingAgent 未集成到 Agent Router**
   - 新建的 `VoiceBookingAgent` 未导出到 `src/server/agent/__init__.py`
   - `src/server/main.py` 仍使用旧的 mock `BookingAgent`

3. **端到端流程未拉通**

## 下一步工作

### Priority 1: 调研 agent-browser

```bash
# 1. 查看 agent-browser SDK 文档
# 2. 了解 API 接口
# 3. 评估替换方案
```

### Priority 2: 重构 BrowserController

```
原方案: BrowserController → Chrome DevTools MCP
新方案: BrowserController → agent-browser (Vercel)
```

**保持不变的接口**：
- `navigate(url)`
- `evaluate_script(script)`
- `take_snapshot()`
- `extract_hotel_data()`

### Priority 3: 集成 VoiceBookingAgent 到 Agent Router

## 关键文件

| 文件 | 说明 | 状态 |
|------|------|------|
| `src/server/agent/voice_booking_agent.py` | VoiceBookingAgent | ✅ 完成 |
| `src/server/agent/tools/stage_tool_wrapper.py` | Stage Tool 包装器 | ✅ 完成 |
| `src/server/browser/stages/*.py` | 7 个 Stage Tools | ✅ 完成 |
| `src/server/browser/browser_controller.py` | 浏览器控制器 | ⚠️ 需重构 |
| `src/server/agent/router.py` | Agent 路由 | ❌ 未修改 |
| `src/server/main.py` | 入口 | ❌ 未修改 |

## 测试命令

```bash
# 运行所有测试
.venv/bin/python -m pytest tests/unit/browser/test_stages.py tests/integration/browser/test_booking_flow.py tests/integration/agent/test_voice_booking_agent.py -v

# 预期结果: 62 passed
```

## 架构说明（新）

```
┌─────────────────────────────────────────────────────────────┐
│ VoiceBookingAgent (LLM + Tool Orchestration)                  │
│  - Interprets NL: "第二个" → index=2                        │
│  - Calls Stage Tools sequentially                            │
└─────────────────┬───────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ StageToolWrapper                                             │
│  - Wraps BookingStage as @tool                              │
└─────────────────┬───────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage Tools (browser/stages/*.py)                            │
│  - Return StageResult with action/data/options              │
└─────────────────┬───────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ BrowserController (NEW: agent-browser instead of CDP)        │
│  - navigate, evaluate_script, take_snapshot, extract_hotel   │
└─────────────────────────────────────────────────────────────┘
```

## Git Log

```
b486ef4 docs: add handover documentation for next session
d05bbd3 feat(agent): add StageToolWrapper and VoiceBookingAgent for NL-based booking
6ac31a9 feat(browser): add retry mechanism and session pause/resume
abd236b docs(tasks): add implementation task list for browser booking
da1cb92 docs(plan): add Phase 1 planning artifacts for browser booking
d4daeae docs(spec): add Browser Booking Automation specification
```

---

**Handoff 准备完成。下一个 session 先调研 agent-browser，然后决定如何重构 BrowserController。**
