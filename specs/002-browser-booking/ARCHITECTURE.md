# Browser Booking - Architecture & Decisions

**Created**: 2026-03-28
**Updated**: 2026-03-28 (Q7-Q13 answered)
**Status**: Requirements Collection Complete

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
│   └── [7 Stage Tools]
│       ├── book_hotel_search
│       ├── book_hotel_select_hotel
│       ├── book_hotel_select_room
│       ├── book_hotel_confirm_selection
│       ├── book_hotel_fill_guest
│       └── book_hotel_finalize
│
├── BrowserController
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

## 4. Tool Output Schema

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

## 5. 待确认/待设计

### 5.1 UI 交互设计 (子 Agent)
- 截图 + 结构化数据展示
- 前端如何渲染酒店列表、房间选项

### 5.2 Agent SOUL + Audit Agent (子 Agent)
- 主 Agent SOUL 定义 (防止跑偏)
- Audit Agent 架构 (输入输出审查)

### 5.3 登录检测
- 需要探索: 检测 booking.com 是否已登录
- 方法: 访问某页面, 检查是否被重定向到登录页

### 5.4 UserProfile 接口
- 抽象接口, 后期可能接 RAG/Database
- 初期实现: 写死返回用户信息

---

## 5. UI Design (from sub-agent)

### 5.1 Layout Structure

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

### 5.2 Screenshot Strategy

| Scenario | Trigger | Compression |
|----------|---------|-------------|
| Stage enters | `stage_update` | JPEG 70% |
| Action completed | Browser automation completes | JPEG 70% |
| Periodic refresh | Every 5s during browsing | JPEG 50% |
| User requested | `screenshot_request` | PNG lossless |
| Error state | Error message | PNG lossless |

### 5.3 WebSocket Messages

**Backend → Frontend**: `stage_update`, `screenshot_update`, `action_required`, `structured_data`, `error`, `booking_confirmed`
**Frontend → Backend**: `user_selection`, `voice_command`, `navigate_back`, `cancel_booking`

---

## 6. Agent SOUL (from sub-agent)

### 6.1 SELF (Identity)

```
OpenClaw Voice Booking Agent - 酒店预订自动化助手
- 角色: Booking.com 酒店预订的 co-pilot
- 范围: 仅限酒店预订
- 语言: 中英双语
- 边界: 不完成支付、不存储敏感数据、不修改已预订房间
```

### 6.2 OPERATING SYSTEM (规则)

| 规则 | 说明 |
|------|------|
| OS-001 | 不完成支付 - 支付页面必须交由用户手动完成 |
| OS-002 | 不存储敏感数据 - 不缓存信用卡、CVV |
| OS-003 | 用户确认 - 酒店选择、房间选择、住客信息必须确认 |
| OS-004 | 不离开 Booking.com |
| OS-005 | 最多5间房 |
| OS-006 | 只创建新预订，不修改已有预订 |

### 6.3 Refusal Conditions

- 非酒店预订请求 ("天气怎么样？")
- 超过5间房
- 要求输入支付信息
- 修改已有预订
- 恶意意图

### 6.4 Clarification Triggers

- 缺少目的地/日期
- 模糊的选择 (便宜的？)
- 矛盾的需求
- 页面异常

---

## 7. Audit Agent Architecture (from sub-agent)

### 7.1 Position

Wrapper pattern around BookingAgent, integrated via LangChain `BaseCallbackHandler`

### 7.2 Pre-Audit Checks

- Intent Classification (on-topic vs off-topic)
- Parameter Validation (required params, range)
- Safety Check (SOUL rule compliance)
- Loop Detection (same tool called 3x)

### 7.3 Post-Audit Checks

- Page State Validation (DOM state matches expected)
- Data Extraction (correctly parsed)
- Price Reasonableness (within 10x expected)
- Stage Progression (moved forward)

### 7.4 Intervention Levels

| Level | Type | Use Case |
|-------|------|----------|
| 1 | Soft (Warning) | Minor concern, append clarification |
| 2 | Hard (Block) | SOUL violation, refuse action |
| 3 | Emergency (Abort) | Malicious intent, repeated failures |

### 7.5 Metrics Tracked

- Turn count (>50 warn)
- Error rate (>5 consecutive errors)
- Loop count (>3 same action)
- Time since progress (>2 min)

---

## 6. 待办事项

### P1 - 当前迭代
- [ ] Python MCP SDK 集成 (`uv add mcp`)
- [ ] BrowserController 实现
- [ ] 7 个 Stage Tools 实现
- [ ] TurnContext 状态持久化
- [ ] 登录检测探索
- [ ] 重试机制 (3次)

### P2 - 后续迭代
- [ ] Agent SOUL 定义
- [ ] Audit Agent 架构
- [ ] UserProfile (RAG/Database)
- [ ] UI 交互详细设计

---

## 7. Reference

- OpenClaw Booking Skill: `specs/002-browser-booking/SKILL.md`
- Agent Layer Spec: `specs/001-agent-layer/spec.md`
