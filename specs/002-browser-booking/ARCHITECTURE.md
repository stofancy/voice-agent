# Browser Booking - Architecture & Decisions

**Created**: 2026-03-28
**Updated**: 2026-03-28 (Q&A 完整整合)
**Status**: Requirements Collection Complete

---

## 0. Q&A 答案汇总

### Q&A 记录 (from transcript + 探索)

| Q# | 问题 | 答案摘要 |
|----|------|---------|
| Q1 | Browser 操作范围 | Booking.com only，复杂交互见 SKILL.md，浏览器内支付，成功=到支付页 |
| Q5 | 超时/错误处理 | 需要更长超时，暂不考虑重试 |
| Q6 | 多阶段实现 | **B: 每个 Stage 独立 Tool**，避免 LangChain stream 阻塞前端 |
| Q7 | 用户输入意图识别 | 会话概念，当前会话中理解 "the second one" |
| Q8 | Browser Session 归属 | User Session 绑定，暂时单用户 |
| Q10 | Tool 输出内容 | 结构化数据 + 推荐建议，自然语言告知用户 |
| Q11 | Session 归属确认 | User Session → Browser Session + TurnContext，确认正确 |
| Q12 | 架构关系 | BrowserController 从属于 Stage Tools，不是并列 |
| Q13 | 工具抽象层 | 保持灵活性，后期可替换为 API |
| Q14 | 日期处理 | LLM 判断，Session 初始化时提供 System Context |
| Q15 | 语言/货币 | 取决于 Booking.com，需要告诉用户货币种类 |
| Q16 | 错误处理 | LLM 判断 |
| Q17 | 用户纠正机制 | LLM 先行判断是否需要特殊处理 |
| Q18 | 支付页面 | 无需监控，用户手动完成 |
| Q25 | 数据提取方式 | A11Y Tree 是语义化层（role + name + state），但输出大（>90KB），需分块处理；**价格数据不在 DOM 中**，需通过截图视觉提取或进入详情页 |

### 关键架构确认

1. **BrowserController 从属于 Stage Tools**（不是并列关系）
2. **Response 三段式结构**：收到请求 → 正在做什么 → 结果（数据+建议）
3. **自然语言选择**：支持 "第二个"、"贵一点的"、"带早餐的" 等

---

## 1. Key Design Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| KB-001 | Chrome DevTools MCP via Python SDK | 官方 `mcp` 包, stdio transport |
| KB-002 | 每个 Stage 独立 LangChain Tool | 前端透明, 支持暂停/恢复 |
| KB-003 | TurnContext.current_stage | 跨请求恢复状态 |
| KB-004 | WebSocket Session 绑定 Browser Session | 单用户, 简单生命周期 |
| KB-005 | 标准化 JSON 输出 {stage, data, action} | 统一接口 |
| KB-006 | 纯自然语言 Tool 输入 | 前端不解析, LLM 处理 |
| KB-007 | 自定义 Chrome Profile: `voice-agent` | 保持登录状态 |
| KB-008 | 检测已有 Chrome, 否则新启动 | 资源复用 |
| KB-009 | 非 headless, 用户可见操作过程 | 需要用户手动输入支付信息 |
| KB-010 | 需要登录则登录, 否则不管 | 尊重 Booking.com 要求 |
| KB-011 | 支持 Back/回退 | 用户可改变主意 |
| KB-012 | ActivityId 标记 Browser Session | 前端生成, 同一 ID 复用 Browser |
| KB-013 | 15min 整体, 3min 单次 Browser, 2min 用户输入 | - |
| KB-014 | 单一 BookingAgent, 7 个 stage tools | Agent 根据用户输入自主决策使用哪个 tool |
| KB-015 | LLM 自己理解意图并决策 | 不限制用户输入顺序，Agent 理解后缓存并适时使用 |
| KB-016 | 提前提供信息可跳过等待 | 用户提前给房型 → 匹配后直接继续，前端显示通知 |
| KB-017 | 需要 Browser 操作日志 | 用于调试、审计 |
| KB-018 | 只支持中文 | TTS 为中文准备 |

---

## 2. Architecture

### 2.1 Component Diagram

```
VoiceTurn
├── BookingAgent (LangChain)
│   └── [7 Stage Tools] ←── BrowserController (从属)
│       ├── book_hotel_search ──→ BrowserController.snapshot()
│       ├── book_hotel_select_hotel ──→ BrowserController.click()
│       ├── book_hotel_select_room ──→ BrowserController.fill()
│       ├── book_hotel_confirm_selection
│       ├── book_hotel_fill_guest
│       └── book_hotel_finalize
│
├── BrowserController (每个 Stage Tool 持有)
│   ├── MCP Client (启动独立进程)
│   ├── Session 管理
│   └── 弹窗处理
│
└── TurnContext
    ├── current_stage
    ├── booking_data
    └── browser_session_id (ActivityId)
```

### 2.2 MCP Integration

```python
# BrowserController 启动时
from mcp import ClientSession, StdioServerParameters

server_params = StdioServerParameters(
    command="npx",
    args=["chrome-devtools-mcp", "--browserUrl", "http://127.0.0.1:9222"]
)
```

### 2.3 Chrome Profile

- Profile 名称: `voice-agent`
- macOS 路径: `~/Library/Application Support/Google/Chrome/`
- 启动参数: `--remote-debugging-port=9222 --user-data-dir=<profile_path>`

---

## 3. 7-Stage Flow

```
Search → Results → Property → Room → Selection → Guest → Payment
```

| Stage | Tool | User Input | Action |
|-------|------|-----------|--------|
| 1. Search | `book_hotel_search` | ❌ | CONTINUE |
| 2. Results | `book_hotel_select_hotel` | ✅ 选择酒店 | WAIT_FOR_SELECTION |
| 3. Property | `book_hotel_navigate_property` | ❌ | CONTINUE |
| 4. Room | `book_hotel_select_room` | ✅ 选择房间 | WAIT_FOR_SELECTION |
| 5. Selection | `book_hotel_confirm_selection` | ❌ | CONTINUE |
| 6. Guest | `book_hotel_fill_guest` | ✅ 填写信息 | CONTINUE |
| 7. Payment | `book_hotel_finalize` | ❌ | COMPLETE |

---

## 4. Response 三段式结构

每轮 Response 分三部分告知用户：

| 阶段 | 目的 | 示例 |
|------|------|------|
| a. 收到请求 | 确认理解，准备执行 | "我理解您想预订巴黎4月1-5日的酒店..." |
| b. 正在做什么 | 状态更新，持续反馈 | "正在搜索巴黎的酒店..." |
| c. 结果 | 展示数据，建议，等待抉择 | "找到3家酒店，您想要哪个？" |

### Response 数据结构

```json
{
  "turn_id": "abc123",
  "stage": "hotel_selection",
  "response": {
    "text": "I found 3 hotels in Paris...",
    "data": {
      "type": "hotel_list",
      "items": [
        {
          "id": "h1",
          "display": "Hotel A - $150/night",
          "details": {...},
          "recommendation_score": 0.95,
          "recommendation_reason": "Best value with high rating"
        }
      ]
    },
    "action": {
      "type": "WAIT_FOR_SELECTION",
      "allow_auto_proceed": false,
      "timeout_seconds": 120
    }
  }
}
```

### 自然语言选择模式

| 用户说 | 解析为 |
|--------|--------|
| "第二个" / "the second one" | 选择列表第2项 |
| "贵一点的" / "the more expensive one" | 按价格排序后选 |
| "带早餐的" / "with breakfast" | 按条件过滤 |
| "评分最高的" / "best rated" | 按评分排序 |
| "那个" / "that one" | 确认当前选中项 |
| "不是" / "not that" | 拒绝当前选项，重新选择 |
| "换一批" / "show me others" | 重新搜索/展示更多 |

---

## 5. Tool Output Schema

```json
{
  "stage": "results",
  "data": {
    "hotels": [
      {"id": "h1", "name": "Hotel A", "price": "$500", "rating": "8.5"}
    ]
  },
  "action": {
    "type": "WAIT_FOR_SELECTION",
    "message": "I found 2 hotels. Which one?",
    "options": [
      {"index": 1, "description": "Hotel A - $500/night"},
      {"index": 2, "description": "Hotel B - $800/night"}
    ]
  }
}
```

### Action Types

| Type | 说明 | 前端行为 |
|------|------|---------|
| `CONTINUE` | 自动继续 | 显示进度 |
| `WAIT_FOR_SELECTION` | 等待选择 | 显示选项 |
| `WAIT_FOR_CONFIRMATION` | 等待确认 | 显示摘要 |
| `COMPLETE` | 结束 | 显示结果 |
| `ERROR` | 错误 | 显示错误 |

---

## 6. UI Design

### 6.1 Layout Structure

```
┌──────────────────────────────────────────────────────────────────────────┐
│  [●] Search ─── [○] Results ─── [○] Property ─── [○] Room ─── [○] ─── [○] │
│                                      Selection ─── [○] Guest ─── [○]      │
│                                                                 Payment   │
├─────────────────────────────────────┬──────────────────────────────────────┤
│         Browser Viewport            │       Structured Data Panel         │
│   ┌─────────────────────────────┐   │   ┌────────────────────────────┐     │
│   │    [Screenshot Feed]         │   │   │  Hotel Card / Room Card / │     │
│   │                             │   │   │  Guest Form / Payment      │     │
│   └─────────────────────────────┘   │   └────────────────────────────┘     │
│   Action Required: "Select a hotel" │   Voice: "pick #1", "first"        │
├─────────────────────────────────────┴──────────────────────────────────────┤
│  [                    Voice / Text Input Field                    ]      │
└──────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Screenshot Strategy

| Scenario | Trigger | Compression |
|----------|---------|-------------|
| Stage enters | `stage_update` | JPEG 70% |
| Action completed | Browser automation completes | JPEG 70% |
| Periodic refresh | Every 5s during browsing | JPEG 50% |
| User requested | `screenshot_request` | PNG lossless |
| Error state | Error message | PNG lossless |

### 6.3 WebSocket Messages

**Backend → Frontend**: `stage_update`, `screenshot_update`, `action_required`, `structured_data`, `error`, `booking_confirmed`
**Frontend → Backend**: `user_selection`, `voice_command`, `navigate_back`, `cancel_booking`

---

## 7. Agent SOUL

### 7.1 SELF (Identity)

```
OpenClaw Voice Booking Agent - 酒店预订自动化助手
- 角色: Booking.com 酒店预订的 co-pilot
- 范围: 仅限酒店预订
- 语言: 中英双语
- 边界: 不完成支付、不存储敏感数据、不修改已预订房间
```

### 7.2 OPERATING SYSTEM (规则)

| 规则 | 说明 |
|------|------|
| OS-001 | 不完成支付 - 支付页面必须交由用户手动完成 |
| OS-002 | 不存储敏感数据 - 不缓存信用卡、CVV |
| OS-003 | 用户确认 - 酒店选择、房间选择、住客信息必须确认 |
| OS-004 | 不离开 Booking.com |
| OS-005 | 最多5间房 |
| OS-006 | 只创建新预订，不修改已有预订 |

### 7.3 Refusal Conditions

- 非酒店预订请求 ("天气怎么样？")
- 超过5间房
- 要求输入支付信息
- 修改已有预订
- 恶意意图

### 7.4 Clarification Triggers

- 缺少目的地/日期
- 模糊的选择 (便宜的？)
- 矛盾的需求
- 页面异常

---

## 8. Audit Agent Architecture

### 8.1 Position

Wrapper pattern around BookingAgent, integrated via LangChain `BaseCallbackHandler`

### 8.2 Pre-Audit Checks

- Intent Classification (on-topic vs off-topic)
- Parameter Validation (required params, range)
- Safety Check (SOUL rule compliance)
- Loop Detection (same tool called 3x)

### 8.3 Post-Audit Checks

- Page State Validation (DOM state matches expected)
- Data Extraction (correctly parsed)
- Price Reasonableness (within 10x expected)
- Stage Progression (moved forward)

### 8.4 Intervention Levels

| Level | Type | Use Case |
|-------|------|----------|
| 1 | Soft (Warning) | Minor concern, append clarification |
| 2 | Hard (Block) | SOUL violation, refuse action |
| 3 | Emergency (Abort) | Malicious intent, repeated failures |

### 8.5 Metrics Tracked

- Turn count (>50 warn)
- Error rate (>5 consecutive errors)
- Loop count (>3 same action)
- Time since progress (>2 min)

---

## 9. 待办事项

### P1 - 当前迭代
- [ ] Python MCP SDK 集成 (`uv add mcp`)
- [ ] BrowserController 实现
- [ ] 7 个 Stage Tools 实现
- [ ] TurnContext 状态持久化
- [ ] **登录检测探索** ← 需实际探索
- [ ] 重试机制 (3次)

### P2 - 后续迭代
- [x] Agent SOUL 定义 ✅ (已设计)
- [x] Audit Agent 架构 ✅ (已设计)
- [ ] UserProfile (RAG/Database)
- [x] UI 交互详细设计 ✅ (已设计)

### P0 - 探索阶段
- [x] **Chrome DevTools MCP 实际能力验证** ✅
  - `list_pages`, `new_page`, `navigate_page` ✅
  - `take_snapshot`, `take_screenshot` ✅
  - `click`, `fill` ✅
  - 快照输出大（>100KB），需分块处理或用截图
- [x] **Booking.com 流程验证** ✅
  - 启动参数: `--remote-debugging-port=9222`
  - Consent 弹窗: checkbox "Select all" → button "Agree"
  - 弹窗处理: 多语言弹窗、Genius 优惠弹窗需关闭
  - 搜索表单: `combobox` (目的地) + `button` (日期) + `button` (人数/房间) + `button` (搜索)
  - 搜索结果 URL: `searchresults.html?ss=Tokyo&...`
  - 登录检测: 检查 DOM 是否有 "Sign in" / "Register" 链接
- [x] **Q23/Q24 探索** ✅
  - 日期选择: 点击 "Check-in date" 按钮 → 日历弹出 → 点击日期选择
  - 人数/房间: 点击人数按钮 → 下拉菜单选择
  - 确认日期后需重新点击 Search 按钮
- [x] **Q25 数据提取探索** ✅
  - 酒店名称: `document.querySelectorAll('[data-testid="property-card"]')` ✅
  - 评分: 可通过 DOM 提取 ✅
  - **价格: 不在 DOM 中，需截图或进入详情页**

### KB-019: Booking.com 弹窗处理
- Consent 弹窗: checkbox "Select all" → button "Agree"
- 其他弹窗: "Dismiss" 或 "Stay on Booking.com Global"

---

## 10. Reference

- OpenClaw Booking Skill: `specs/002-browser-booking/SKILL.md`
- Agent Layer Spec: `specs/001-agent-layer/spec.md`
