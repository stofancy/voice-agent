# Agent Layer 实现分析

**Created**: 2026-03-28
**Updated**: 2026-03-28 (Phase 7 Complete)
**Status**: 技术验证完成 ✅

---

## 核心发现：框架优先 vs 业务实现

**确认**：当前实现的是**框架性代码**，实际订票业务逻辑都是 Mock。

### Phase 7 状态：✅ 完成

| Task | 说明 | 状态 |
|------|------|------|
| T031 | docs/agent-layer.md | ✅ |
| T032 | TOOL_PROGRESS_MESSAGES 清理 | ✅ |
| T033 | 功能性冒烟测试 | ✅ 新增 |
| T034 | 集成测试 | ✅ |
| T035 | Security audit | ✅ |
| T036 | Structured logging + correlation IDs | ✅ |
| T037 | Stream gap metrics logging | ✅ |
| T038 | Router decision logging | ✅ |
| T039 | Benchmark (skipped - mocks 无意义) | ✅ |

**测试结果**: 105 tests passing (79 unit + 26 integration)

### 框架层（已实现 ✅）

| 组件 | 状态 | 说明 |
|------|------|------|
| LangChain Agent 封装 | ✅ | `LangChainAgent` with `astream_events()` |
| 非阻塞 Stream | ✅ | 500ms progress emit, backpressure queue |
| AgentRouter | ✅ | 关键词分类路由 |
| BookingAgent | ✅ | 封装 + prompt 模板 |
| QueryAgent | ✅ | 封装 + prompt 模板 |
| 超时机制 | ✅ | 30s 全局超时 |
| 取消机制 | ✅ | TurnContext + StreamController |
| Structured Logging | ✅ | Correlation IDs for request tracing |
| 集成测试 | ✅ | 26 tests |

### 业务逻辑层（Mock/未实现 ❌）

| 组件 | 当前状态 | 问题 |
|------|----------|------|
| `search_hotels` | 硬编码返回 2 个假酒店 | 无真实 API |
| `book_hotel` | 生成假 booking_id | 无真实支付/确认流程 |
| `get_weather` | 随机假数据 | 无 OpenWeather API |
| `web_search` | 硬编码假结果 | 无搜索 API |
| `get_time` | `datetime.now()` | 基本可用，但非业务关键 |

---

## 已知 Bug（暂不修复）

以下 bug 已知但因优先级低暂不修复：

1. **`AgentCompleteEvent.full_response` 空字符串**
   - 位置: `booking_agent.py:69`, `query_agent.py:68`
   - 原因: `astream()` 是流式接口，`full_response` 需要累积完所有 chunk 才能得到
   - 影响: 不影响核心功能，`ainvoke()` 路径正确

2. **FR-007a per-tool timeout 未实现**
   - 位置: `TOOL_TIMEOUT_SECONDS = 30.0` (全局)
   - 原因: 需要改 tool 接口定义
   - 影响: 不影响当前 mock 工具测试

3. **多轮对话状态累积**
   - 原因: 每次 TurnContext 是新创建的
   - 影响: 需要外部 (voice_turn.py) 传入 conversation_history

---

## 需求层面问题分析

### 1. 框架优先的产品策略

当前是 **"先跑通框架，后填入业务"** 的开发模式：
- ✅ 好处: 证明了技术可行性，streaming/routing/cancellation 都能工作
- ❌ 坏处: 不能真正用于生产，无法完成实际订票

### 2. 订票流程实际缺失

**用户期望的订票流程**:
```
1. 用户: "我要订酒店"
2. Agent: 询问地点、日期、人数
3. 用户: 提供信息
4. Agent: 调用真实酒店 API → 返回真实可用房间
5. 用户: 选择房间
6. Agent: 调用支付 API → 真实扣款
7. Agent: 返回真实 booking confirmation
```

**当前实现的订票流程**:
```
1. 用户: "我要订酒店"
2. Agent: "Let me search..." (LLM 生成)
3. search_hotels: 返回假酒店列表 (Mock)
4. Agent: "I found 2 hotels..." (LLM 生成)
5. book_hotel: 生成假 booking_id (Mock)
6. Agent: "Your booking BK123 is confirmed." (LLM 硬编码格式)
```

### 3. 性能测量缺失

| Task | 说明 | 状态 |
|------|------|------|
| T033 | 测量 stream gap，目标 <200ms | ✅ 功能性测试完成 |
| T037 | stream gap 指标记录 | ✅ 已实现 |
| T039 | 有/无 streaming 性能对比 | ⚠️ 跳过（mock 无意义）|

**结论**: 无法用 mock 数据验证 SC-001 (<200ms)，但框架逻辑正确

---

## 待办事项

- [ ] **TBD**: 评估并决定是否在 Browser Booking 前修复以下问题

### Bug 修复评估

| Bug | 严重度 | 修复工作量 | 建议 |
|-----|--------|------------|------|
| `AgentCompleteEvent.full_response` 空字符串 | 低 | 小 | 需求挖掘后再决定 |
| Per-tool timeout 未实现 | 低 | 中 | 需求挖掘后再决定 |
| 多轮对话状态累积 | 中 | 小 | 需求挖掘后再决定 |

### 修复选项

#### Option A: 当前路线 - 先不做修复

1. 保持当前 bug 不修复
2. 继续做 Browser Booking (新 feature branch)
3. 在 Browser Booking 开发过程中如果需要，再回头修复

**适合场景**: 快速验证 Browser Booking 可行性

#### Option B: 修复后再做 Browser Booking

1. 先修复 `AgentCompleteEvent` bug
2. 实现 per-tool timeout
3. 确认多轮状态累积问题
4. 然后再做 Browser Booking

**适合场景**: 希望技术债务更少

---

## 决策点

1. **当前 Agent Layer 的目标是什么？**
   - 技术验证/演示 → Option A
   - 生产就绪 → Option B
   - 平衡速度与完整性 → Option A (Browser Booking 过程中按需修复)

2. **订票流程是否需要真实实现？**
   - 如果是: 需要真实 API 凭证、支付网关接入
   - 如果否: Mock 足够，继续优化框架

3. **性能测量是否重要？**
   - 如果是: 需要接入真实 API 后再测量
   - 如果否: 可以推迟到 Browser Booking 验证后

---

## 下一步

1. **当前 branch (001-agent-layer) 技术验证完成** ✅
2. **等待 merge main**
3. **新开 feature branch 做 Browser Booking** (SDD 流程)

---

*本分析旨在客观评估当前实现状态，确认技术验证完成，业务逻辑仍为 Mock。*
