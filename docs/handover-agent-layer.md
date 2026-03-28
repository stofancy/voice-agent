# Handover Document: Agent Layer (001-agent-layer)

**Date**: 2026-03-28
**Branch**: `001-agent-layer`
**Status**: Ready for PR to merge to `main`

---

## 1. Summary

Agent Layer 技术验证完成，基于 LangChain agent 的 non-blocking stream 框架已实现。

### 完成状态

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Setup | T001-T003 | ✅ Complete |
| Phase 2: Foundational | T004-T010 | ✅ Complete |
| Phase 3: US1 | T011-T016 | ✅ Complete |
| Phase 4: US2 | T017-T021 | ✅ Complete |
| Phase 5: US3 | T022-T026 | ✅ Complete |
| Phase 6: US4 | T027-T030 | ✅ Complete |
| Phase 7: Polish | T031-T039 | ✅ Complete |
| Phase 8: Bug Fixes | T040-T047 | ✅ Complete |

**Total**: 47 tasks ✅ Complete

### 测试结果

- 105 tests passing (79 unit + 26 integration)
- 9/9 smoke tests passing

---

## 2. 已实现的框架能力

### 核心组件

| 组件 | 文件 | 说明 |
|------|------|------|
| `LangChainAgent` | `src/server/agent/langchain_agent.py` | 封装 LangChain astream_events，支持 non-blocking tool execution |
| `BookingAgent` | `src/server/agent/booking_agent.py` | 酒店预订专用 Agent |
| `QueryAgent` | `src/server/agent/query_agent.py` | 信息查询专用 Agent (weather/search/time) |
| `AgentRouter` | `src/server/agent/router.py` | 关键词分类路由 |
| `StreamController` | `src/server/agent/stream_controller.py` | 回调控制，支持取消 |
| `BackpressureQueue` | `langchain_agent.py` | 事件队列，背压控制 max_depth=100 |

### 工具

| 工具 | 文件 | 状态 |
|------|------|------|
| `search_hotels` | `tools/hotel_tool.py` | Mock - 返回假酒店列表 |
| `book_hotel` | `tools/hotel_tool.py` | Mock - 生成假 booking_id |
| `get_weather` | `tools/query_tool.py` | Mock - 随机假数据 |
| `web_search` | `tools/query_tool.py` | Mock - 硬编码假结果 |
| `get_time` | `tools/query_tool.py` | Mock - datetime.now() |

### 机制

| 机制 | 状态 | 说明 |
|------|------|------|
| 500ms progress emit | ✅ | `_emit_periodic_progress()` |
| 30s tool timeout | ✅ | `emit_timeout()` |
| Cancellation | ✅ | `TurnContext` + `StreamController.is_cancelled` |
| Backpressure | ✅ | `BackpressureQueue` max_depth=100 |
| Structured Logging | ✅ | Correlation ID (`turn_id`) |
| Intent Routing | ✅ | 关键词分类 |

---

## 3. 已知限制

### Mock 工具

所有工具都是 Mock 实现，不能用于真实订票：
- `search_hotels` 硬编码返回 2 个假酒店
- `book_hotel` 生成假 booking_id
- 查询工具返回随机/假数据

### 未实现的 Bug (低优先级)

| Bug | 说明 | 影响 |
|-----|------|------|
| `AgentCompleteEvent.full_response=""` | astream 接口中 full_response 未填充 | 不影响 invoke() 路径 |
| Per-tool timeout 未实现 | 全局 30s 超时 | Browser 操作可能 >30s |
| 多轮状态累积 | 需要外部传入 conversation_history | voice_turn.py 处理 |

---

## 4. 新增文件

| 文件 | 说明 |
|------|------|
| `tests/integration/test_agent_layer.py` | 26 个集成测试 |
| `tests/integration/__init__.py` | 测试目录初始化 |
| `specs/001-agent-layer/ANALYSIS.md` | 实现分析文档 |
| `docs/handover-agent-layer.md` | 本文档 |

---

## 5. 修改的文件

| 文件 | 修改内容 |
|------|----------|
| `src/server/agent/langchain_agent.py` | `turn_id` 参数, structured logging, `web_search`/`get_time` progress messages |
| `src/server/agent/stream_controller.py` | `turn_id` 支持, structured logging |
| `src/server/turn_context.py` | 已有 `turn_id` 字段 |
| `specs/001-agent-layer/tasks.md` | Phase 7 完成, T033/T037/T039 重新定义为功能性测试 |
| `specs/001-agent-layer/ANALYSIS.md` | 新增分析文档 |

---

## 6. 下一步

### 立即

1. **Create PR**: 将 `001-agent-layer` merge 到 `main`
2. **Code Review**: 检查所有变更

### 之后 (新 Branch)

**Browser Booking Feature** (新 branch `002-browser-booking`)

基于已完成的讨论：

**架构要点**：
- 每个 Stage 是独立 LangChain Tool (非单一 book_hotel tool)
- Browser Session 由 VoiceTurn 管理，与 User Session 绑定
- Stage Tools 操作 BrowserSession，返回结构化数据
- Response Builder 输出 text + data + action 三部分

**Response 结构**：
```json
{
  "turn_id": "abc123",
  "stage": "hotel_selection",
  "response": {
    "text": "I found 3 hotels...",
    "data": {
      "type": "hotel_list",
      "items": [...],
      "filter_options": [...],
      "sort_options": [...]
    },
    "action": {
      "type": "WAIT_FOR_SELECTION",
      "allow_auto_proceed": false
    }
  }
}
```

**用户交互设计**：
- 三段式：收到请求 → 正在做什么 → 结果展示
- 自然语言选择："第二个"、"贵一点的"、"带早餐的"
- 错误可纠正："不是那个"、"换一批"

**待探索**：
- PlayWright vs Chrome MCP 技术选型
- Booking.com 官方 API 集成 (最终目标)
- 日期/语言/货币处理细节

---

## 7. 关键文档位置

```
specs/001-agent-layer/
├── spec.md              # 功能规格
├── plan.md              # 实施计划
├── tasks.md             # 任务列表 (47/47 ✅)
├── ANALYSIS.md          # 实现分析 (新增)
└── checklists/          # 质量检查清单

docs/
└── handover-agent-layer.md  # 本文档
```

---

## 8. 命令参考

```bash
# 运行测试
.venv/bin/python -m pytest tests/unit/agent/ tests/integration/test_agent_layer.py -v

# 烟雾测试
.venv/bin/python scripts/smoke_test_agent.py

# 创建 PR
gh pr create --title "feat(agent): complete agent layer for non-blocking tool calls" --body "$(cat <<'EOF'
## Summary
- LangChain Agent 框架实现完成
- Non-blocking stream (500ms progress emit)
- Multi-agent routing (BookingAgent, QueryAgent)
- Cancellation + backpressure support
- 105 tests passing

## Test plan
- [x] Unit tests (79)
- [x] Integration tests (26)
- [x] Smoke tests (9/9)
EOF
)"
```
