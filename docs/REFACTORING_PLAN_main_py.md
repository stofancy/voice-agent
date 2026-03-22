# main.py 重构方案

**版本**: v1.0
**创建时间**: 2026-03-22
**状态**: 待评审

---

## 问题分析

### 1. "Closure Soup" 问题

`websocket_endpoint` 函数（477行）包含过多嵌套函数和共享状态：

| 嵌套函数 | 通过 `nonlocal` 捕获的变量 |
|---------|--------------------------|
| `send_listening_stopped_once()` | `connection_state` |
| `run_turn()` | `connection_state`, `last_transcript`, `last_response`, `last_perf_data` |
| `cancel_response()` | `response_task` |

**问题**：难以推理执行流、无法独立测试、无法复用逻辑。

### 2. 模块未连接

| 模块 | 类/函数 | 状态 | 问题 |
|------|---------|------|------|
| `connection.py` | `ConnectionStateMachine` | **未连接** | 使用字符串 `connection_state = "IDLE"` |
| `connection.py` | `WebSocketConnection` | 部分连接 | 在 `run_turn()` 内部创建 |
| `audio.py` | `AudioBuffer` | **未连接** | 使用原始 `list[np.ndarray]` |
| `messages.py` | `parse_message()` | **未连接** | 使用原始 `json.loads()` |
| `voice_turn.py` | `VoiceTurn` | **未连接** | 类存在但从未实例化 |
| `streaming_synthesis.py` | `StreamingSynthesis` | **已连接** ✓ | 使用正确 |

### 3. SRP 违反

| 位置 | 问题 | 应该是 |
|------|------|--------|
| `websocket_endpoint` | 处理连接认证、音频缓冲、VAD、消息路由、对话编排、取消、错误处理 | 拆分为 `ConnectionManager`, `MessageRouter`, `TurnExecutor` |
| `run_turn()` | 做 STT、合成编排、性能收集、WS 发送、错误处理、取消 | 替换为 `VoiceTurn.execute()` |
| 消息循环 | 12 个 case 分支做不同事情 | 替换为 `MessageRouter.route()` |
| `startup()` | 内联初始化所有服务 | 使用 `ServiceFactory` 或依赖注入 |

### 4. OCP 违反

| 位置 | 问题 | 应该允许 |
|------|------|---------|
| 消息类型匹配 | 硬编码 `if/elif` 处理 `msg_type` | 新增消息类型只需添加处理器，不修改路由 |
| `send_listening_stopped_once()` | 硬编码 JSON 结构 | 应该使用类型化 `WSMessage` 对象 |
| WebSocket 发送方法 | 原始字典构建 | 应该使用 `WebSocketConnection` 类型化发送方法 |
| 状态机 | 原始字符串 `"IDLE"`/`"LISTENING"` | 应该使用 `ConnectionStateMachine` |

---

## 设计原则

1. **单一职责**：每个类/模块只有一个清晰的变更原因
2. **开闭原则**：对扩展开放，对修改关闭（新增消息类型只需添加处理器，不修改路由）
3. **Clean Code**：小函数、清晰命名、适当抽象

---

## 目标架构

```
websocket_endpoint
├── _validate_ws_auth()                    # auth.py - 已分离 ✓
├── SessionManager                         # NEW: 拥有连接生命周期
│   ├── ConnectionStateMachine            # 替换字符串状态
│   ├── AudioBuffer                       # 替换原始列表
│   ├── TurnContext                       # NEW: 每次对话的状态+取消
│   └── TurnManager                       # NEW: 编排 VoiceTurn
│       └── VoiceTurn.execute()
│           └── StreamingSynthesis.run()
│               └── TurnContext.cancelled  # 取消检查
└── MessageRouter                         # NEW: 替换 elif 链
    ├── StartListeningHandler
    ├── StopListeningHandler
    ├── AudioHandler (with VAD)
    ├── InterruptHandler
    └── PingHandler
```

---

## 模块职责

### 3.1 `turn_context.py` (NEW)

**文件**: `src/server/turn_context.py`

**职责**：
- 每次对话的状态（transcript, response, metrics）
- 共享取消标志，`StreamingSynthesis` 循环检查
- 音频缓冲访问

**接口**:
```python
@dataclass
class TurnContext:
    """Per-turn context shared between VoiceTurn and StreamingSynthesis."""
    cancelled: asyncio.Event
    audio_data: Optional[np.ndarray] = None
    transcript: str = ""
    full_response: str = ""
    perf_data: dict = field(default_factory=dict)

    def cancel(self):
        self.cancelled.set()

    def is_cancelled(self) -> bool:
        return self.cancelled.is_set()

    def reset(self):
        self.cancelled.clear()
        self.audio_data = None
        self.transcript = ""
        self.full_response = ""
        self.perf_data = {}
```

### 3.2 `turn_manager.py` (NEW)

**文件**: `src/server/turn_manager.py`

**职责**：
- 创建和执行 `VoiceTurn`
- 处理取消（调用 `TurnContext.cancel()`）
- 跟踪 `response_task`

**接口**:
```python
class TurnManager:
    def __init__(self, ws: WebSocketConnection, state_machine: ConnectionStateMachine):
        self._ws = ws
        self._state_machine = state_machine
        self._current_turn: Optional[VoiceTurn] = None
        self._response_task: Optional[asyncio.Task] = None

    async def start_turn(self, audio_data: np.ndarray, turn_context: TurnContext):
        """Start a new voice turn."""

    async def cancel_turn(self):
        """Cancel current turn and send interrupt_complete."""
```

### 3.3 `message_router.py` (NEW)

**文件**: `src/server/message_router.py`

**职责**：
- 替换 12 个 elif 分支
- 对新消息类型开放（添加处理器，不修改路由器）

**接口**:
```python
class MessageRouter:
    def __init__(self, handlers: dict[MessageType, MessageHandler]):
        self._handlers = handlers

    async def route(self, message: WSMessage, session: SessionProtocol):
        handler = self._handlers.get(message.type)
        if handler:
            await handler.handle(message, session)
```

### 3.4 已存在模块

| 模块 | 现有类/函数 | 需要修改 |
|------|------------|---------|
| `connection.py` | `ConnectionStateMachine`, `WebSocketConnection` | 替换字符串状态 |
| `audio.py` | `AudioBuffer` | 替换原始列表 |
| `messages.py` | `parse_message()`, `WSMessage` 类型 | 替换原始 json.loads |
| `voice_turn.py` | `VoiceTurn` | 修复接口，添加 `TurnContext` 支持 |
| `streaming_synthesis.py` | `StreamingSynthesis` | 添加 `TurnContext` 取消检查 |

---

## 分步迁移计划

每步可独立验证。

### Step 1: 连接 `AudioBuffer`（无行为变更）

**目标**：用 `AudioBuffer` 类替换原始 `list[np.ndarray]`

**修改文件**:
- `src/server/main.py`

**改动**:
```python
# main.py line 248
# BEFORE:
audio_buffer: list[np.ndarray] = []

# AFTER:
from .audio import AudioBuffer
audio_buffer = AudioBuffer()

# Line 406-407: 替换拼接
# BEFORE:
audio_data = np.concatenate(audio_buffer)
audio_buffer = []

# AFTER:
audio_data = audio_buffer.concatenate()
audio_buffer.clear()
```

**验证**: `test_msg_001_start_listening_clears_buffer_and_sets_state` 应通过

---

### Step 2: 连接 `ConnectionStateMachine`（无行为变更）

**目标**：用 `ConnectionStateMachine` 替换字符串 `connection_state`

**修改文件**:
- `src/server/main.py`

**改动**:
```python
# Line 247: 添加导入并替换状态
from .connection import ConnectionStateMachine
connection_state = ConnectionStateMachine()

# 替换所有字符串比较:
# BEFORE: if connection_state != "LISTENING"
# AFTER:  if not connection_state.is_listening()

# BEFORE: connection_state = "LISTENING"
# AFTER:  connection_state.transition_to(ConnectionState.LISTENING)

# BEFORE: connection_state = "IDLE"
# AFTER:  connection_state.transition_to(ConnectionState.IDLE)

# 等等...
```

**验证**: 状态机相关测试应通过

---

### Step 3: 在 Endpoint 作用域连接 `WebSocketConnection`

**目标**：在 endpoint 入口创建一次 `WebSocketConnection`，不在 `run_turn()` 内部创建

**修改文件**:
- `src/server/main.py`

**改动**:
```python
# websocket.accept() 后，创建一次 WebSocketConnection:
await websocket.accept()
ws_connection = WebSocketConnection(websocket)

# 传递 ws_connection 给 run_turn() 而非新建:
async def run_turn(audio_data: np.ndarray, ws_conn: WebSocketConnection):
    ...
    synthesis = StreamingSynthesis(
        llm=backend,
        tts=tts,
        websocket=ws_conn,  # 使用传入的连接
        ...
    )
```

**验证**: `test_pipeline_001_full_pipeline` 应通过

---

### Step 4: 创建 `TurnContext` 并连接取消逻辑

**目标**：用 `TurnContext.cancel()` 替换嵌套的 `cancel_response()`

**创建文件**:
- `src/server/turn_context.py`

**修改文件**:
- `src/server/main.py`
- `src/server/streaming_synthesis.py`

**验证**: `test_pipeline_005_cancel` 应通过

---

### Step 5: 将 `run_turn()` 提取到 `VoiceTurn.execute()`

**目标**：用 `VoiceTurn.execute()` 替换嵌套的 `run_turn()` 函数

**修改文件**:
- `src/server/voice_turn.py`
- `src/server/main.py`

**注意**: `StreamingSynthesis.run()` 需要接受 `TurnContext` 以进行取消检查

**验证**: 所有 `TURN-*` 测试应通过

---

### Step 6: 连接 `parse_message()` - 替换原始 json 解析

**目标**：使用 `messages.parse_message()` 替代 `json.loads()`

**修改文件**:
- `src/server/main.py`

**验证**: 消息处理测试应通过

---

### Step 7: 用 Message Handler Map 替换 elif 链

**目标**：用策略模式替换 12 个 elif 分支

**创建文件**:
- `src/server/message_router.py`

**修改文件**:
- `src/server/main.py`

**验证**: 所有 `MSG-*` 测试应通过

---

## 文件变更汇总

| 步骤 | 文件 | 操作 | 目的 |
|------|------|------|------|
| 1 | `src/server/audio.py` | 已存在 | 使用 `AudioBuffer` |
| 2 | `src/server/connection.py` | 已存在 | 使用 `ConnectionStateMachine` |
| 3 | `src/server/messages.py` | 已存在 | 使用 `parse_message()` |
| 4 | `src/server/voice_turn.py` | 修改 | 修复接口 |
| 5 | `src/server/streaming_synthesis.py` | 修改 | 接受 `TurnContext` |
| 6 | `src/server/turn_context.py` | **新建** | 每次对话状态+取消 |
| 7 | `src/server/turn_manager.py` | **新建** | 对话生命周期管理 |
| 8 | `src/server/message_router.py` | **新建** | 替换 elif 链 |
| 9 | `src/server/main.py` | 修改 | 连接所有模块 |

---

## TTS Provider 考虑：`bailian_realtime`

`bailian_realtime` provider 使用 `RealtimeTTSStream`，采用 `feed/finish` 模式。

**取消挑战**：`RealtimeTTSStream` 在首次 `feed()` 时懒连接，无原生取消支持。

**通过 `TurnContext` 解决**:
```python
# In StreamingSynthesis.tts_consume_loop():
async for audio_chunk in tts_stream:
    if turn_context.is_cancelled():
        # 排空剩余块但不发送给客户端
        continue
    # 正常：发送给客户端
```

---

## 验证清单

每步完成后，运行相应测试：

| 步骤 | 测试 |
|------|------|
| 1 | `test_msg_001_start_listening_clears_buffer_and_sets_state` |
| 2 | 状态机相关测试 |
| 3 | `test_pipeline_001_full_pipeline` |
| 4 | `test_pipeline_005_cancel` |
| 5 | `test_turn_001_*` 到 `test_turn_004_*` |
| 6 | 消息解析测试 |
| 7 | 所有 `MSG-*` 测试 |

完整测试：`pytest tests/unit/test_main_websocket.py -v`

---

## 总结

此重构将 `main.py` 从"闭包汤"转换为清晰架构：

1. **消除嵌套函数** - `run_turn()`, `cancel_response()`, `send_listening_stopped_once()` 成为适当的类/方法
2. **替换字符串状态** - `ConnectionStateMachine` 强制有效转换
3. **替换原始集合** - `AudioBuffer`, `TurnContext`
4. **替换 elif 链** - `MessageRouter` 策略模式
5. **连接现有模块** - `parse_message()`, `VoiceTurn`, `StreamingSynthesis`

每步可独立验证，全程保持测试覆盖。
