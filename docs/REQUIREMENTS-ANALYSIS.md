# Voice Agent Channel Plugin - 需求分析报告

**文档状态**: 撰写中  
**创建日期**: 2026-03-16  
**最后更新**: 2026-03-16  
**作者**: 羲和

---

## 文档结构

- [x] **第一部分：项目概述与核心目标** (已完成)
- [x] **第二部分：整体架构设计** (已完成)
  - [x] 2.1 系统架构总览
  - [x] 2.2 组件分层与职责
  - [x] 2.3 UI 架构设计
  - [x] 2.4 部署架构
- [x] **第三部分：组件详细设计** (已完成)
  - [x] 3.1 WebSocket Server
  - [x] 3.2 STT Client
  - [x] 3.3 TTS Client
  - [x] 3.4 Session Manager
  - [x] 3.5 Channel Plugin
  - [x] 3.6 Inbound Handler
  - [x] 3.7 Outbound Handler
  - [x] 3.8 VoiceAgentClient (浏览器 SDK)
- [ ] **第四部分：消息流程分析**
- [ ] **第五部分：OpenClaw Channel Plugin 集成**
- [ ] **第六部分：UI 交互设计详解**
- [ ] **第七部分：技术实现细节**
- [ ] **第八部分：现状 Gap 分析**
- [ ] **第九部分：实施计划**

---

# 第一部分：项目概述与核心目标

## 1.1 项目背景

### 1.1.1 为什么需要 Voice Agent？

传统的 AI 交互方式主要依赖**文本输入/输出**：
- 用户需要打字输入问题
- AI 返回文本回答
- 用户阅读文本

这种方式存在明显局限：
1. **交互效率低** — 打字比说话慢得多
2. **使用场景受限** — 驾驶、运动、双手占用时无法使用
3. **用户体验割裂** — 不符合人类自然的交流方式

**Voice Agent 的目标**：实现**自然语音对话**体验
- 用户说话 → 自动识别为文本
- AI 处理并回复
- 回复自动合成为语音播放

### 1.1.2 为什么采用 OpenClaw Channel Plugin 架构？

**关键洞察**：Voice Agent 不是一个独立应用，而是 **OpenClaw 生态系统中的一个消息渠道**。

```
┌─────────────────────────────────────────────────────────┐
│                    OpenClaw Gateway                      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Telegram   │  │    Discord   │  │    Signal    │  │
│  │   Channel    │  │   Channel    │  │   Channel    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                          ...                            │
│  ┌──────────────┐                                       │
│  │  Voice Agent │  ← 新增：语音交互渠道                │
│  │   Channel    │                                       │
│  └──────────────┘                                       │
│                                                          │
│                    ↓                                     │
│            ┌──────────────┐                             │
│            │  Agent Core  │  ← 统一的 AI 处理能力        │
│            └──────────────┘                             │
└─────────────────────────────────────────────────────────┘
```

**采用 Channel Plugin 的优势**：

| 优势 | 说明 |
|------|------|
| **复用 Agent 能力** | 无需重新实现 AI 逻辑，直接使用 OpenClaw 的 Agent |
| **统一架构** | 与其他 channel (Telegram/Discord) 保持一致的集成方式 |
| **配置管理** | 使用 OpenClaw 统一的配置系统 |
| **消息路由** | 复用 OpenClaw 的消息路由和会话管理 |
| **技能系统** | 直接使用 OpenClaw 的 skills 机制 |

### 1.1.3 参考实现：openclaw-lark

**openclaw-lark** 是一个成熟的 Channel Plugin 实现，支持飞书/Lark 消息平台。

**Voice Agent 与 openclaw-lark 的对比**：

| 方面 | openclaw-lark | voice-agent |
|------|---------------|-------------|
| **消息来源** | 飞书 WebSocket/Event | 浏览器 WebSocket |
| **消息类型** | 文本、图片、文件、卡片 | 音频流、文本 |
| **输入处理** | 直接接收文本 | 音频 → STT → 文本 |
| **输出处理** | 直接发送文本 | 文本 → TTS → 音频 |
| **Agent 集成** | `dispatchReplyFromConfig` | **待实现** |

**核心借鉴点**：
1. Channel Plugin 的接口定义和生命周期管理
2. 消息的 inbound/outbound 处理流程
3. 与 OpenClaw Gateway 的集成方式
4. 配置管理和账户系统

---

## 1.2 核心目标

### 1.2.1 P0 目标（MVP - 浏览器端）

**目标描述**：实现基于浏览器的语音交互能力

**用户故事**：
> 作为用户，我希望在浏览器中点击录音按钮说话，然后听到 AI 的语音回复。

**功能需求**：

| ID | 需求 | 验收标准 |
|----|------|----------|
| F1 | 浏览器录音 | 点击按钮开始录音，再次点击停止 |
| F2 | 音频传输 | 录音数据通过 WebSocket 发送到服务端 |
| F3 | 语音识别 | 服务端将音频转换为文本 (STT) |
| F4 | Agent 集成 | 将 STT 文本发送到 OpenClaw Agent |
| F5 | 语音合成 | 将 Agent 回复转换为音频 (TTS) |
| F6 | 音频播放 | 浏览器播放 TTS 音频 |
| F7 | 状态显示 | 实时显示当前状态（录音中/处理中/播放中） |

**技术需求**：

| ID | 需求 | 说明 |
|----|------|------|
| T1 | WebSocket 服务器 | 监听浏览器连接，处理音频流 |
| T2 | STT 集成 | 阿里百炼 qwen3-asr-flash |
| T3 | TTS 集成 | 阿里百炼 qwen3-tts-instruct-flash |
| T4 | Channel Plugin | 符合 OpenClaw Plugin SDK 规范 |
| T5 | OpenClaw 集成 | 调用 Agent 处理用户输入 |

### 1.2.2 P1 目标（增强功能）

**目标描述**：提升用户体验和系统稳定性

| ID | 需求 | 说明 |
|----|------|------|
| E1 | 流式 STT | 边说话边识别，减少等待时间 |
| E2 | 流式 TTS | 边合成边播放，降低首字延迟 |
| E3 | VAD 检测 | 自动检测语音结束，无需手动停止 |
| E4 | 打断功能 | TTS 播放中可打断，立即响应新指令 |
| E5 | 错误处理 | 完善的错误提示和重试机制 |
| E6 | 会话管理 | 支持多用户并发连接 |

### 1.2.3 P2 目标（长期扩展）

**目标描述**：扩展到更多平台

| ID | 需求 | 说明 |
|----|------|------|
| X1 | Android 客户端 | 原生 App 支持 |
| X2 | 智能音箱 | Alexa/Google Home 集成 |
| X3 | 全双工对话 | 支持实时双向语音流 |
| X4 | 多模态交互 | 语音 + 视觉结合 |

---

## 1.3 关键设计决策

### 1.3.1 为什么选择 WebSocket？

**备选方案对比**：

| 方案 | 延迟 | 复杂度 | 浏览器支持 | 选择 |
|------|------|--------|-----------|------|
| HTTP Polling | 高 | 低 | 好 | ❌ |
| Server-Sent Events | 中 | 中 | 好 | ❌ (仅单向) |
| WebRTC | 低 | 高 | 好 | ❌ (过度复杂) |
| **WebSocket** | **低** | **中** | **好** | ✅ |

**选择 WebSocket 的理由**：
1. **双向通信** — 同时支持音频上传和下载
2. **低延迟** — 长连接，无需重复握手
3. **成熟稳定** — 所有现代浏览器支持
4. **与 OpenClaw 一致** — Gateway 本身使用 WebSocket

### 1.3.2 音频格式选择

**决策**：PCM 16kHz 16bit mono

**理由**：
1. **STT 要求** — 阿里百炼 ASR 支持的标准格式
2. **带宽友好** — 16kHz 对人声足够，数据量适中
3. **处理简单** — PCM 无需编解码，直接处理
4. **TTS 兼容** — 输出格式一致，无需转换

**数据量计算**：
```
16000 samples/s × 2 bytes × 1 channel = 32 KB/s
100ms 分块 = 3.2 KB/块
```

### 1.3.3 STT/TTS 服务商选择

**决策**：阿里百炼 (DashScope)

**理由**：
1. **质量优秀** — 中文识别准确率高
2. **成本合理** — 相比 OpenAI/Google 更经济
3. **延迟可控** — 国内访问速度快
4. **API 稳定** — 有完善的 SDK 和文档

**API 模型**：
- STT: `qwen3-asr-flash`
- TTS: `qwen3-tts-instruct-flash`

---

## 1.4 成功指标

### 1.4.1 功能指标

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| STT 准确率 | > 95% | TTS→STT 闭环测试 |
| 端到端延迟 | < 3s | 录音结束到 TTS 开始播放 |
| 并发用户数 | ≥ 10 | 压力测试 |
| 服务可用性 | > 99% | 运行时间监控 |

### 1.4.2 用户体验指标

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| 首字延迟 | < 1.5s | STT 完成到开始播放 |
| 自然度评分 | > 4/5 | 用户主观评价 |
| 错误率 | < 1% | 失败请求占比 |

---

## 1.5 范围界定

### 1.5.1 本项目包含

- ✅ WebSocket 服务器实现
- ✅ 浏览器客户端 SDK
- ✅ STT/TTS 集成
- ✅ OpenClaw Channel Plugin
- ✅ 基础 WebUI 演示

### 1.5.2 本项目不包含

- ❌ 独立 Agent 实现（复用 OpenClaw）
- ❌ 多模态交互（纯语音）
- ❌ 移动端原生 App（仅浏览器）
- ❌ 智能音箱集成（长期目标）

---


---

# 第二部分：整体架构设计

## 2.1 系统架构总览

### 2.1.1 宏观架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          用户侧 (Browser)                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        WebUI (React + TypeScript)                │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │    │
│  │  │  VoiceButton │  │   Waveform   │  │  Transcript  │          │    │
│  │  │  (录音控制)  │  │  (波形动画)  │  │  (实时字幕)  │          │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │    │
│  │                              ↓                                   │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │              VoiceAgentClient (WebSocket SDK)             │   │    │
│  │  │  - MediaRecorder (录音)  - AudioContext (播放)            │   │    │
│  │  │  - PCM 编码/解码          - 状态管理                       │   │    │
│  │  └──────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              ↕ WebSocket (端口 8765)                     │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼────────────────────────────────────────┐
│              OpenClaw Gateway 进程 (Node.js + TypeScript)                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              voice-agent plugin (运行在 Gateway 进程内)           │   │
│  │  ┌───────────────────────────────────────────────────────────┐ │   │
│  │  │  VoiceAgentWebSocketServer                                │ │   │
│  │  │  - 连接管理  - 会话管理  - 消息路由  - 状态广播            │ │   │
│  │  └───────────────────────────────────────────────────────────┘ │   │
│  │           ↓                    ↓                    ↓           │   │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │   │
│  │  │   STT Client    │ │   TTS Client    │ │  Session Mgr    │   │   │
│  │  │  (阿里百炼 ASR) │ │  (阿里百炼 TTS) │ │  (会话生命周期) │   │   │
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘   │   │
│  │           ↓                    ↓                    ↓           │   │
│  │  ┌───────────────────────────────────────────────────────────┐ │   │
│  │  │  Inbound Handler  │  Outbound Handler  │  Channel Plugin  │ │   │
│  │  │  (消息解析→Gateway)│(Gateway 回复→TTS)  │  (OpenClaw 集成)  │ │   │
│  │  └───────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                ↓ 通过 api.runtime (进程内调用)          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              OpenClaw Gateway Core                               │   │
│  │  ┌───────────────────────────────────────────────────────────┐ │   │
│  │  │  Agent Core (LLM + Skills)                                │ │   │
│  │  │  - 对话管理  - 工具调用  - 记忆系统  - 流式响应            │ │   │
│  │  └───────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

**关键说明**：
- **voice-agent plugin** 运行在 **OpenClaw Gateway 进程内**（不是独立服务）
- **WebSocket Server** 是 plugin 的一部分，监听 8765 端口
- **STT/TTS/Session** 都在 plugin 内，通过进程内调用与 Gateway 通信
- **浏览器** 通过 WebSocket 直连 plugin，无中间服务器

### 2.1.2 核心组件清单

| 层级 | 组件 | 技术栈 | 文件位置 | 职责 |
|------|------|--------|----------|------|
| **UI 层** | VoiceButton | React + Framer Motion | `packages/webui/src/components/` | 录音按钮，带波形动画 |
| **UI 层** | Waveform | React + Canvas | `packages/webui/src/components/` | 实时音频波形可视化 |
| **UI 层** | Transcript | React | `packages/webui/src/components/` | 实时字幕显示 |
| **UI 层** | StatusIndicator | React | `packages/webui/src/components/` | 连接状态指示器 |
| **SDK 层** | VoiceAgentClient | TypeScript + WebSocket | `packages/webui/src/lib/` (待确认) | 浏览器 WebSocket 客户端 |
| **SDK 层** | useRecorder Hook | React Hooks + MediaRecorder | `packages/webui/src/hooks/` | 麦克风录音逻辑 |
| **SDK 层** | voiceStore | Zustand | `packages/webui/src/store/` | 全局状态管理 |
| **Plugin 层** | WebSocketServer | Node.js + ws | `packages/server/src/websocket/` | WebSocket 连接管理 |
| **Plugin 层** | SessionManager | Node.js | `packages/server/src/session/` | 会话生命周期管理 |
| **Plugin 层** | STTClient | OpenAI SDK (兼容) | `packages/server/src/stt/` | 语音识别 API 调用 |
| **Plugin 层** | TTSClient | Python 脚本调用 | `packages/server/src/tts/` | 语音合成 API 调用 |
| **Plugin 层** | Channel Plugin | OpenClaw Plugin SDK | `packages/server/src/channel/` | OpenClaw 插件注册 |
| **Plugin 层** | Inbound Handler | TypeScript | `packages/server/src/messaging/inbound/` | 消息解析 → Gateway |
| **Plugin 层** | Outbound Handler | TypeScript | `packages/server/src/messaging/outbound/` | Gateway 回复 → 浏览器 |

---

## 2.2 组件分层与职责

### 2.2.1 四层架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: UI 层 (Presentation)                              │
│  - 用户可见的界面组件                                        │
│  - 用户交互处理                                              │
│  - 状态可视化                                                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: SDK 层 (Client Logic)                             │
│  - WebSocket 通信                                            │
│  - 音频编解码                                                │
│  - 本地状态管理                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: 服务端层 (Server Logic)                           │
│  - 连接管理                                                  │
│  - STT/TTS 处理                                              │
│  - 会话管理                                                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: 集成层 (Integration)                              │
│  - OpenClaw Channel Plugin                                  │
│  - Gateway 集成                                              │
│  - Agent 调用                                                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2.2 各层职责详解

#### Layer 1: UI 层

**核心组件**：

| 组件 | 文件位置 | 职责 |
|------|----------|------|
| `App.tsx` | `packages/webui/src/App.tsx` | 主应用容器，状态协调 |
| `VoiceButton` | `packages/webui/src/components/VoiceButton.tsx` | 录音按钮 |
| `Waveform` | `packages/webui/src/components/Waveform.tsx` | 实时波形动画 |
| `Transcript` | `packages/webui/src/components/Transcript.tsx` | 字幕显示 |
| `StatusIndicator` | `packages/webui/src/components/StatusIndicator.tsx` | 状态指示器 |

**状态来源**：
- 本地状态：录音中、播放中
- 服务端推送：连接状态、处理状态、错误信息

**UI 状态机**：
```
         ┌──────────┐
         │  离线    │
         └────┬─────┘
              │ 连接
              ↓
         ┌──────────┐
         │  已连接  │◄─────────┐
         └────┬─────┘          │
              │ 点击录音        │
              ↓                │
         ┌──────────┐          │
         │  录音中  │──────────┤
         └────┬─────┘  取消/停止
              │ 说话结束        │
              ↓                │
         ┌──────────┐          │
         │  处理中  │──────────┤
         └────┬─────┘  错误
              │ STT 完成        │
              ↓                │
         ┌──────────┐          │
         │  播放中  │──────────┘
         └────┬─────┘
              │ 播放完成
              ↓
         ┌──────────┐
         │  完成    │
         └──────────┘
```

#### Layer 2: SDK 层

**核心模块**：

| 模块 | 文件位置 | 职责 |
|------|----------|------|
| `VoiceAgentClient` | `packages/webui/src/lib/VoiceAgentClient.ts` (待确认) | WebSocket 客户端封装 |
| `useRecorder` | `packages/webui/src/hooks/useRecorder.ts` | MediaRecorder Hook |
| `voiceStore` | `packages/webui/src/store/voiceStore.ts` | Zustand 状态管理 |
| `audioUtils` | `packages/webui/src/utils/audio.ts` | 音频编解码工具 |

**关键功能**：

1. **WebSocket 连接管理**
   - 自动重连
   - 心跳保活
   - 连接状态通知

2. **音频处理**
   - MediaRecorder 录音
   - PCM 16kHz 编码
   - Base64 转换
   - AudioContext 播放

3. **状态同步**
   - 本地状态 → 服务端（录音开始/停止）
   - 服务端状态 → 本地（处理中/播放中）

#### Layer 3: Plugin 层（服务端逻辑）

**核心模块**：

| 模块 | 文件位置 | 职责 |
|------|----------|------|
| `WebSocketServer` | `packages/server/src/websocket/server.ts` | WebSocket 服务器 |
| `SessionManager` | `packages/server/src/session/manager.ts` | 会话管理 |
| `STTClient` | `packages/server/src/stt/client.ts` | STT API 调用 |
| `TTSClient` | `packages/server/src/tts/client.ts` | TTS API 调用 |
| `Inbound Handler` | `packages/server/src/messaging/inbound/handler.ts` | 入站消息处理 |
| `Outbound Handler` | `packages/server/src/messaging/outbound/outbound.ts` | 出站消息处理 |

**关键功能**：

1. **连接管理**
   - 用户认证（pairing）
   - 会话创建/销毁
   - 连接注册/注销

2. **消息路由**
   - 音频 → STT → Inbound Handler
   - Outbound Handler → TTS → 音频

3. **状态管理**
   - 会话状态追踪
   - 超时检测
   - 并发控制

#### Layer 4: 集成层（OpenClaw 集成）

**核心模块**：

| 模块 | 文件位置 | 职责 |
|------|----------|------|
| `Channel Plugin` | `packages/server/src/channel/plugin.ts` | OpenClaw 插件定义 |
| `Plugin Config` | `packages/server/openclaw.plugin.json` | 插件元数据 |

**关键功能**：

1. **插件注册**
   - 向 OpenClaw 注册 voice-agent channel
   - 定义配置 schema
   - 实现 lifecycle hooks

2. **Gateway 集成**
   - Inbound: 消息 → Gateway → Agent
   - Outbound: Agent 回复 → 浏览器

3. **配置管理**
   - API Key 管理
   - 会话参数配置
   - 安全策略配置

---

## 2.3 UI 架构设计

### 2.3.1 UI 组件树

```
App (packages/webui/src/App.tsx)
├── VoiceLayout (packages/webui/src/components/)
│   ├── StatusIndicator (连接状态)
│   ├── VoiceCard
│   │   ├── VoiceButton (录音控制)
│   │   ├── Waveform (波形动画)
│   │   └── Transcript (字幕)
│   └── ConnectionState (连接信息)
└── TypingEffect (打字机效果)
```

### 2.3.2 UI 状态管理

**使用 Zustand 进行全局状态管理**：

```typescript
interface VoiceState {
  // 连接状态
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  
  // 录音状态
  isRecording: boolean;
  audioLevel: number;  // 用于波形动画
  
  // 播放状态
  isPlaying: boolean;
  audioQueue: AudioChunk[];
  
  // 字幕
  transcript: string;
  isTranscriptFinal: boolean;
  
  // 错误
  error: string | null;
  
  // 动作
  connect: () => Promise<void>;
  disconnect: () => void;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  playAudio: (base64: string) => void;
  updateTranscript: (text: string, isFinal: boolean) => void;
}
```

### 2.3.3 UI 交互流程

**核心交互**：

```
用户点击录音按钮
       ↓
请求麦克风权限
       ↓
开始录音 + 发送音频流
       ↓
UI 显示波形动画 + "录音中"状态
       ↓
用户停止录音
       ↓
发送"停止"控制消息
       ↓
UI 显示"处理中"状态
       ↓
接收 STT 转录结果
       ↓
UI 显示字幕（草稿 → 最终）
       ↓
接收 TTS 音频流
       ↓
UI 显示"播放中"状态 + 波形动画
       ↓
播放完成
       ↓
UI 返回"完成"状态
```

### 2.3.4 UI 视觉设计规范

**设计风格**：ChatGPT Voice Mode 风格

| 元素 | 设计规范 |
|------|----------|
| **主色调** | 深色背景 (#1A1A2E) + 渐变色（紫/蓝/青） |
| **录音按钮** | 圆形，带脉冲动画 |
| **波形** | 5-7 根动态条形，随音量变化 |
| **字幕** | 居中显示，白色文字，带淡入效果 |
| **状态指示器** | 小圆点，颜色随状态变化 |

**状态颜色**：

| 状态 | 颜色 | 说明 |
|------|------|------|
| 离线 | 灰色 (#666) | 未连接 |
| 连接中 | 黄色 (#FFC107) | 正在建立连接 |
| 已连接 | 绿色 (#4CAF50) | 可以录音 |
| 录音中 | 红色 (#F44336) | 正在录音 |
| 处理中 | 蓝色 (#2196F3) | STT/Agent 处理 |
| 播放中 | 紫色 (#9C27B0) | TTS 播放 |
| 错误 | 橙红色 (#FF5722) | 发生错误 |

### 2.3.5 响应式设计

**断点**：

| 断点 | 宽度 | 布局调整 |
|------|------|----------|
| Mobile | < 640px | 单列，大按钮 |
| Tablet | 640px - 1024px | 居中卡片 |
| Desktop | > 1024px | 最大宽度限制 |

---

## 2.4 部署架构

### 2.4.1 核心部署原则

**关键约束**：voice-agent Plugin **必须**与 OpenClaw Gateway 运行在**同一进程/实例**。

**原因**：
1. Plugin 通过 `api.runtime` 访问 OpenClaw SDK（进程内 API）
2. Plugin 生命周期由 Gateway 管理（启动/停止同步）
3. WebSocket Server 是 Plugin 的一部分，在 Gateway 进程内启动

**对比 openclaw-lark**：

| 方面 | openclaw-lark | voice-agent |
|------|---------------|-------------|
| **消息来源** | 飞书服务器（外部） | 浏览器直连（无中间层） |
| **Plugin 角色** | 被动接收（Webhook 推送） | 主动监听（启动 WebSocket Server） |
| **中间服务器** | 有（飞书） | 无（浏览器直连 Plugin） |

---

### 2.4.2 部署拓扑

```
┌─────────────────────────────────────────────────────────────────┐
│  服务器（云服务器 / 本地主机）                                    │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │           OpenClaw Gateway 进程                            │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  voice-agent plugin (运行在 Gateway 进程内)           │ │ │
│  │  │  ┌───────────────────────────────────────────────┐ │ │ │
│  │  │  │  WebSocket Server (端口 8765)                  │ │ │ │
│  │  │  │  - 监听浏览器连接                               │ │ │ │
│  │  │  │  - STT 处理 (音频 → 文本)                       │ │ │ │
│  │  │  │  - TTS 处理 (文本 → 音频)                       │ │ │ │
│  │  │  └───────────────────────────────────────────────┘ │ │ │
│  │  │                                                     │ │ │
│  │  │  ┌───────────────────────────────────────────────┐ │ │ │
│  │  │  │  OpenClaw Core                                 │ │ │ │
│  │  │  │  - Gateway WebSocket (端口 7777)               │ │ │ │
│  │  │  │  - Agent Core (LLM + Skills)                   │ │ │ │
│  │  │  └───────────────────────────────────────────────┘ │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                    ↑                                      │ │
│  │                    │ 进程内调用 (api.runtime)             │ │
│  └────────────────────┼──────────────────────────────────────┘ │
│                       │                                        │
│         ┌─────────────┼─────────────┐                         │
│         │             │             │                         │
│         ↓             ↓             ↓                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │  浏览器 A    │ │  浏览器 B    │ │  浏览器 C    │          │
│  │  (WebSocket) │ │  (WebSocket) │ │  (WebSocket) │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
│         ↖             ↖             ↖                         │
│          └─────────────┴─────────────┘                        │
│                WebSocket 连接 (端口 8765)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2.4.3 组件部署位置

| 组件 | 部署位置 | 说明 |
|------|----------|------|
| **OpenClaw Gateway** | 服务器 | 核心服务进程 |
| **voice-agent plugin** | Gateway 进程内 | 作为插件安装 |
| **WebSocket Server** | Gateway 进程内 (Plugin 中) | 监听 8765 端口 |
| **STT/TTS Client** | Gateway 进程内 (Plugin 中) | 调用阿里百炼 API |
| **WebUI (静态文件)** | CDN / 服务器 / 任意 | 可独立部署 |
| **浏览器** | 用户设备 | 通过 WebSocket 连接 8765 |

---

### 2.4.4 WebUI 部署选项

**唯一可选的部署部分**：WebUI 静态文件

| 选项 | 说明 | 优点 | 缺点 |
|------|------|------|------|
| **CDN 托管** | WebUI 放在 CDN (Vercel/Netlify) | 加载快，独立扩展，免费 | 需要额外配置 CORS |
| **同服务器** | Gateway 同时提供静态文件 | 简单，统一部署 | 占用服务器资源 |
| **本地开发** | 浏览器直接访问服务器 IP | 开发方便 | 生产不适用 |

**推荐**：开发阶段用"同服务器"，生产环境用"CDN 托管"。

---

### 2.4.5 网络要求

| 连接 | 方向 | 端口 | 协议 | 用途 |
|------|------|------|------|------|
| 浏览器 → 服务器 | 入站 | 8765 | WebSocket | 音频流传输 |
| 浏览器 → 服务器 | 入站 | 3000 (可选) | HTTP | WebUI 静态文件 |
| 服务器 → 阿里百炼 | 出站 | 443 | HTTPS | STT/TTS API |
| Gateway 内部 | 本地 | 7777 | WebSocket | Gateway 内部管理 |

---

### 2.4.6 防火墙配置

**云服务器安全组**：

```bash
# 允许入站
允许 TCP 8765  # 浏览器 WebSocket 连接
允许 TCP 3000  # (可选) WebUI 静态文件

# 允许出站
允许 TCP 443   # 阿里百炼 API
```

**本地部署**：

```bash
# 确保端口未被占用
lsof -i :8765
lsof -i :3000
```

---

### 2.4.7 生产环境考虑

**HTTPS/WSS**：

```
浏览器 → WSS (WebSocket Secure) → Plugin
         ↑
     需要 SSL 证书
```

**建议**：
- 使用 Nginx 反向代理处理 SSL
- 配置 WSS 升级到 WebSocket
- 启用 CORS 允许跨域访问

**Nginx 配置示例**：

```nginx
server {
    listen 443 ssl;
    server_name voice-agent.example.com;
    
    # SSL 证书
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # WebSocket 代理
    location /voice-agent/stream {
        proxy_pass http://localhost:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # 静态文件 (可选)
    location / {
        root /var/www/voice-agent-webui;
        try_files $uri /index.html;
    }
}
```

---

**第二部分 完**

---

*下一步：第三部分 - 组件详细设计*

---

# 第三部分：组件详细设计

**说明**：本节深入每个核心组件的内部实现。对于代码中已实现的部分，直接分析现有代码；对于标注"待验证"的部分，表示需要实际运行测试才能确认。

## 3.1 WebSocket Server

**文件位置**: `packages/server/src/websocket/server.ts`

### 3.1.1 职责

- 监听浏览器 WebSocket 连接（默认端口 8765）
- 管理会话生命周期
- 路由消息到对应处理器（音频 → STT，控制 → 状态管理）
- 推送状态和 TTS 音频给浏览器

### 3.1.2 核心代码结构

```typescript
export class VoiceAgentWebSocketServer {
  private wss: WebSocketServer;  // ws 库的服务器实例
  private sessionManager: SessionManager;
  private readonly sessions: Map<string, SessionContext>;  // 会话映射
  private readonly config: VoiceAgentConfig;

  constructor(options: WebSocketServerOptions, sessionManager: SessionManager) {
    // 创建 WebSocket 服务器
    this.wss = new WebSocketServer({
      port: options.port,      // 默认 8765
      host: options.bind ?? '0.0.0.0',
      path: options.path,      // 默认 '/voice-agent/stream'
    });

    this.setupHandlers();  // 设置事件处理器
  }
}
```

### 3.1.3 连接流程

```
1. 浏览器发起 WebSocket 连接
   ↓
2. 服务器接受连接，创建 Session
   ↓
3. 发送初始状态消息 { type: 'status', state: 'idle' }
   ↓
4. 监听消息事件 (ws.on('message'))
   ↓
5. 处理消息 (handleMessage)
   ↓
6. 连接关闭时清理会话
```

### 3.1.4 消息处理

**接收的消息类型**：

| 类型 | 方向 | 内容 |
|------|------|------|
| `connect` | 浏览器 → 服务器 | 用户 ID，建立配对 |
| `audio` | 浏览器 → 服务器 | Base64 编码的 PCM 音频 |
| `control` | 浏览器 → 服务器 | start/stop/interrupt/ping |

**发送的消息类型**：

| 类型 | 方向 | 内容 |
|------|------|------|
| `status` | 服务器 → 浏览器 | 状态变更（idle/listening/processing/speaking） |
| `transcript` | 服务器 → 浏览器 | STT 识别结果（字幕） |
| `agent_text` | 服务器 → 浏览器 | Agent 文本回复 |
| `agent_audio` | 服务器 → 浏览器 | TTS 音频数据 |
| `error` | 服务器 → 浏览器 | 错误信息 |

### 3.1.5 待验证

- [ ] **并发连接数**：当前实现是否有限制？（待查代码）
- [ ] **心跳机制**：是否有 ping/pong 保活？（代码中有 `setInterval` 每 30 秒 ping）
- [ ] **断线重连**：浏览器断线后会话如何处理？（待查 `ws.on('close')` 处理）

---

## 3.2 STT Client

**文件位置**: `packages/server/src/stt/client.ts`

### 3.2.1 职责

- 调用阿里百炼 STT API
- 将 Base64 PCM 音频转换为文本
- 返回识别结果（含语言、情感等元数据，**待验证是否支持**）

### 3.2.2 核心代码

```typescript
export class STTClient {
  private client: OpenAI;  // 使用 OpenAI 兼容 SDK
  private readonly model: string;

  constructor(options: STTClientOptions) {
    this.client = new OpenAI({
      apiKey: options.apiKey,
      baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    });
    this.model = options.model ?? 'qwen3-asr-flash';
  }

  async transcribe(audioBase64: string): Promise<STTResult> {
    // 转换为 data URL 格式
    const dataUrl = `data:audio/wav;base64,${audioBase64}`;
    
    // 调用 OpenAI 兼容 API
    const completion = await this.client.chat.completions.create({
      model: this.model,
      messages: [{
        role: 'user',
        content: [{
          type: 'input_audio',
          input_audio: { data: dataUrl },
        }],
      }],
      stream: false,
    } as any);

    return {
      text: completion.choices[0]?.message?.content ?? '',
      language: (completion.choices[0]?.message?.annotations as any)?.language,
      emotion: (completion.choices[0]?.message?.annotations as any)?.emotion,
    };
  }
}
```

### 3.2.3 技术细节

**音频格式要求**（已在 1.3.2 决策，**已验证**参考官方文档）：
- 格式：PCM 16kHz 16bit mono
- 编码：Base64
- MIME 类型：`audio/wav`（WAV 容器封装 PCM 数据）
- 数据 URL：`data:audio/wav;base64,{base64Data}`
- **官方文档**：`语音识别 API.md` 确认支持 `audio/wav` + Base64

**API 模型**：
- 默认：`qwen3-asr-flash`
- 备选：`qwen3-asr-standard`（备选方案）

**annotations 字段**（**已验证**参考官方文档）：
- 官方返回：`{ emotion: "neutral", language: "zh", type: "audio_info" }`
- 代码实现正确，无需修改

### 3.2.4 待验证

- [ ] **annotations 字段**：阿里百炼 API 是否真的返回 language/emotion？（需实际测试）
- [ ] **流式 STT**：当前实现是非流式的，是否需要支持流式？（设计文档提到但代码未实现）
- [ ] **错误处理**：API 失败时的重试机制？（当前代码直接 throw error）

---

## 3.3 TTS Client

**文件位置**: `packages/server/src/tts/client.ts`

### 3.3.1 职责

- 调用阿里百炼 TTS API
- 将文本合成为 PCM 音频
- 返回音频数据给 WebSocket Server

### 3.3.2 特殊设计：Python 脚本调用

**为什么用 Python**：Node.js dashscope 包不兼容，需要用 Python SDK。

```typescript
export class TTSClient {
  async synthesize(text: string): Promise<TTSResult> {
    const scriptPath = path.join(__dirname, 'tts-synthesize.py');
    const tempOutput = `/tmp/tts-${Date.now()}.wav`;

    // 调用 Python 脚本
    const { stdout, stderr } = await execAsync(
      `ALI_BAILIAN_API_KEY=${this.apiKey} python3 ${scriptPath} ` +
      `"${text}" "${this.model}" "${this.voice}" "${tempOutput}"`
    );

    // 读取生成的音频文件
    const audioData = fs.readFileSync(tempOutput);
    return { audioData: new Uint8Array(audioData) };
  }
}
```

### 3.3.3 Python 脚本（待查）

**文件位置**: `packages/server/src/tts/tts-synthesize.py`（**需确认是否存在**）

**预期功能**：
- 接收文本、模型、语音、输出路径参数
- 调用 dashscope SDK 合成语音
- 保存为 WAV 文件

### 3.3.4 待验证

- [ ] **Python 脚本**：是否存在？功能是否完整？（需检查文件）
- [ ] **流式 TTS**：是否支持边合成边发送？（当前设计是完整文件）
- [ ] **性能**：Python 进程启动开销多大？是否影响延迟？（需实测）
- [ ] **并发**：多个 TTS 请求同时到达时如何处理？（需查是否有队列）

---

## 3.4 Session Manager

**文件位置**: `packages/server/src/session/manager.ts`

### 3.4.1 职责

- 创建/销毁会话
- 追踪会话状态（idle/listening/processing/speaking）
- 管理会话超时

### 3.4.2 核心接口（待查）

```typescript
export interface SessionInfo {
  sessionId: string;
  userId?: string;
  state: SessionState;
  createdAt: number;
  lastActivityAt: number;
  audioChunks: string[];  // 累积的音频块
}

export class SessionManager {
  createSession(): SessionInfo;
  deleteSession(sessionId: string): void;
  touch(sessionId: string): void;  // 更新活动时间
  updateState(sessionId: string, state: SessionState): void;
  destroy(): void;  // 清理所有会话
}
```

### 3.4.3 待验证

- [ ] **超时清理**：是否有定时任务清理过期会话？（需查代码）
- [ ] **状态机**：状态转换是否有验证？（如 listening → processing → speaking）
- [ ] **并发安全**：多用户同时创建会话是否有锁？（需查实现）

---

## 3.5 Channel Plugin

**文件位置**: `packages/server/src/channel/plugin.ts`

### 3.5.1 职责

- 向 OpenClaw 注册 voice-agent channel
- 实现 ChannelPlugin 接口
- 管理 Plugin 生命周期（启动/停止 WebSocket Server）

### 3.5.2 核心结构

```typescript
export const voiceAgentPlugin: ChannelPlugin = {
  id: 'voice-agent',
  
  meta: {
    id: 'voice-agent',
    label: 'Voice Agent',
    selectionLabel: 'Voice Agent (Browser)',
  },
  
  capabilities: {
    chatTypes: ['direct'],
    media: true,
    // ...
  },
  
  gateway: {
    // Gateway 启动时调用
    startAccount: async (ctx) => {
      // 创建并启动 WebSocket Server
      wsServer = new VoiceAgentWebSocketServer({...});
    },
    
    // Gateway 停止时调用
    stopAccount: async (ctx) => {
      // 关闭 WebSocket Server
      wsServer.close();
    },
  },
  
  outbound: voiceAgentOutbound,  // 出站消息处理器
};
```

### 3.5.3 与 OpenClaw 集成（关键！）

**当前问题**：代码中没有调用 `api.runtime.channel.reply.dispatchReplyFromConfig`

**需要实现**：
```typescript
// 在 inbound handler 中
import { pluginRuntime } from '../index';  // 保存的 runtime

await pluginRuntime.channel.reply.dispatchReplyFromConfig({
  ctx: messageContext,
  cfg: config,
  dispatcher: createVoiceAgentDispatcher(ws),
  replyOptions: { ... },
});
```

### 3.5.4 待验证

- [ ] **runtime 保存**：是否有在 index.ts 中保存 `api.runtime`？（需查代码）
- [ ] **Agent 调用**：当前代码是否真的调用了 Agent？（根据之前分析，答案是❌没有）
- [ ] **配置验证**：plugin.json 中的 configSchema 是否完整？（需检查）

---

## 3.6 Inbound Handler

**文件位置**: `packages/server/src/messaging/inbound/handler.ts`

### 3.6.1 职责

- 处理 WebSocket 消息
- 音频消息 → STT → 文本
- 文本消息 → Gateway → Agent

### 3.6.2 处理流程

```
接收消息
  ↓
验证格式 (validateMessage)
  ↓
解析为 MessageContext (parseVoiceMessage)
  ↓
判断类型
  ├─ audio → 累积音频 → STT → 文本 → 调用 Agent
  ├─ text → 直接调用 Agent
  └─ control → 本地处理（不调用 Agent）
```

### 3.6.3 待验证

- [ ] **Gateway 调用**：`runtime.deliver` 是否真的调用了 Agent？（之前分析是❌）
- [ ] **音频累积**：如何判断音频结束？（靠 `isFinal` 标志？）
- [ ] **错误处理**：STT 失败时如何通知浏览器？（需查代码）

---

## 3.7 Outbound Handler

**文件位置**: `packages/server/src/messaging/outbound/outbound.ts`

### 3.7.1 职责

- 发送 Agent 回复给浏览器
- 管理 WebSocket 连接注册
- 支持文本/媒体/音频消息

### 3.7.2 核心功能

```typescript
// 用户连接注册
const userConnections = new Map<string, WebSocket>();

export function registerUserConnection(userId: string, ws: WebSocket): void {
  userConnections.set(userId, ws);
}

// 发送文本
sendText: async (params) => {
  const ws = getUserConnection(params.to);
  ws.send(JSON.stringify({
    type: 'agent_text',
    data: { text: params.text },
  }));
}
```

### 3.7.3 待验证

- [ ] **TTS 触发**：发送文本后是否自动触发 TTS？（需查代码）
- [ ] **音频发送**：是否有 `sendAudio` 方法？（需查代码）
- [ ] **连接管理**：用户断开后是否正确清理？（需查代码）

---

## 3.8 VoiceAgentClient (浏览器 SDK)

**文件位置**: `webui/src/lib/VoiceAgentClient.ts`（**需确认是否存在**）

### 3.8.1 职责

- 管理 WebSocket 连接
- 录音并发送音频
- 接收并播放 TTS 音频
- 状态管理

### 3.8.2 核心接口（设计）

```typescript
class VoiceAgentClient {
  // 连接
  async connect(): Promise<void>;
  async disconnect(): void;
  
  // 录音
  async startRecording(): Promise<void>;
  async stopRecording(): void;
  
  // 回调
  onTranscript: (text: string, isFinal: boolean) => void;
  onAudio: (base64: string) => void;
  onStateChange: (state: string) => void;
  onError: (error: Error) => void;
}
```

### 3.8.3 待验证

- [ ] **文件存在**：是否有独立的 VoiceAgentClient 类？还是分散在 hooks 中？（需查代码）
- [ ] **PCM 编码**：浏览器如何转换 PCM 16kHz？（需查 useRecorder.ts）
- [ ] **音频播放**：如何播放流式音频？（需查代码）

---

**第三部分 完**

---

*下一步：第四部分 - 消息流程分析*

---

# 第四部分：消息流程分析

**说明**：本节通过时序图和流程图展示完整的消息处理流程。所有流程基于当前代码实现，标注"待验证"的部分需要实际运行测试确认。

---

## 4.1 用户录音流程（浏览器 → Plugin）

### 4.1.1 完整时序图

```
用户        浏览器 WebUI        WebSocket        Plugin (Server)
 │               │                  │                  │
 │  点击录音按钮  │                  │                  │
 │ ────────────> │                  │                  │
 │               │  检查连接状态     │                  │
 │               │                  │                  │
 │               │  请求麦克风权限   │                  │
 │               │ ───────────────> │                  │
 │               │                  │                  │
 │   允许/拒绝   │                  │                  │
 │ <─────────── │                  │                  │
 │               │                  │                  │
 │               │  创建 MediaRecorder                │
 │               │                  │                  │
 │               │  开始录音 (100ms 分块)              │
 │               │                  │                  │
 │   说话...     │                  │                  │
 │               │  PCM 编码 + Base64                  │
 │               │                  │                  │
 │               │  WebSocket 发送音频块               │
 │               │ ───────────────> │  接收消息        │
 │               │                  │ ───────────────> │
 │               │                  │                  │ 验证格式
 │               │                  │                  │ 累积音频
 │               │                  │                  │
 │               │                  │  {type:status,   │
 │               │ <─────────────── │  state:listening}│
 │               │ <─────────────── │                  │
 │  显示"录音中" │                  │                  │
 │               │                  │                  │
 │   点击停止    │                  │                  │
 │ ────────────> │                  │                  │
 │               │  停止录音         │                  │
 │               │  发送 isFinal=true │                 │
 │               │ ───────────────> │  接收最终块      │
 │               │                  │ ───────────────> │
 │               │                  │                  │ 触发 STT
 │               │                  │                  │
 │               │  {type:status,   │                  │
 │               │ <─────────────── │  state:processing}│
 │               │ <─────────────── │                  │
 │  显示"处理中" │                  │                  │
```

### 4.1.2 关键代码位置

**浏览器端录音**：
```typescript
// packages/webui/src/hooks/useRecorder.ts
const mediaRecorder = new MediaRecorder(mediaStream, {
  mimeType: 'audio/webm;codecs=opus',
});

mediaRecorder.ondataavailable = async (event) => {
  // 转换为 PCM 16kHz Base64
  const pcmBase64 = await encodeToPCM(event.data);
  
  // 通过 WebSocket 发送
  ws.send(JSON.stringify({
    type: 'audio',
    data: {
      payload: pcmBase64,
      isFinal: false,  // 最后一块为 true
    },
  }));
};
```

**服务端接收**：
```typescript
// packages/server/src/websocket/server.ts
ws.on('message', async (data) => {
  const message = JSON.parse(data);
  
  if (message.type === 'audio') {
    // 累积音频块
    session.audioChunks.push(message.data.payload);
    
    // 收到最终块时触发 STT
    if (message.data.isFinal) {
      await handleAudioMessage(session);
    }
  }
});
```

### 4.1.3 待验证

- [ ] **PCM 编码实现**：`encodeToPCM` 函数是否存在？（需查 `packages/webui/src/utils/audio.ts`）
- [ ] **100ms 分块**：实际分块间隔是多少？（需查 `mediaRecorder.start(100)`）
- [ ] **状态同步**：浏览器是否正确显示"录音中"状态？（需实测）

---

## 4.2 STT 处理流程（音频 → 文本）

### 4.2.1 完整流程图

```
Plugin (Inbound Handler)          STT Client           阿里百炼 API
        │                             │                      │
        │  拼接完整音频                │                      │
        │  completeAudio = chunks.join('')                  │
        │                             │                      │
        │  调用 transcribe()          │                      │
        │ ─────────────────────────> │  构建请求            │
        │                             │ ───────────────────> │
        │                             │  POST /v1/chat/completions
        │                             │  {                   │
        │                             │    model: "qwen3-asr-flash",
        │                             │    messages: [{      │
        │                             │      role: "user",   │
        │                             │      content: [{     │
        │                             │        type: "input_audio",
        │                             │        input_audio: {│
        │                             │          data: "data:audio/wav;base64,..."
        │                             │        }             │
        │                             │      }]              │
        │                             │    }]                │
        │                             │  }                   │
        │                             │                      │
        │                             │  响应                │
        │                             │ <─────────────────── │
        │                             │  {                   │
        │                             │    choices: [{       │
        │                             │      message: {      │
        │                             │        content: "你好",
        │                             │        annotations: [{
        │                             │          language: "zh",
        │                             │          emotion: "neutral"
        │                             │        }]            │
        │                             │      }               │
        │                             │    }]                │
        │                             │  }                   │
        │                             │                      │
        │  返回 STT 结果               │                      │
        │ <───────────────────────── │                      │
        │  { text: "你好", language: "zh" }                 │
        │                             │                      │
        │  发送 transcript 给浏览器   │                      │
        │ ──────────────────────────────────────────────────
        │                             │
```

### 4.2.2 关键代码

```typescript
// packages/server/src/stt/client.ts
async transcribe(audioBase64: string): Promise<STTResult> {
  const dataUrl = `data:audio/wav;base64,${audioBase64}`;
  
  const completion = await this.client.chat.completions.create({
    model: 'qwen3-asr-flash',
    messages: [{
      role: 'user',
      content: [{
        type: 'input_audio',
        input_audio: { data: dataUrl },
      }],
    }],
    stream: false,
  } as any);

  return {
    text: completion.choices[0]?.message?.content ?? '',
    language: (completion.choices[0]?.message?.annotations as any)?.language,
    emotion: (completion.choices[0]?.message?.annotations as any)?.emotion,
  };
}
```

### 4.2.3 待验证

- [ ] **错误处理**：API 失败时是否有重试？（当前代码直接 throw）
- [ ] **延迟**：STT API 平均响应时间？（需实测）

**已验证**（参考官方文档 `语音识别 API.md`）：
- ✅ **MIME 类型**：`audio/wav`（官方文档示例）
- ✅ **annotations 字段**：官方返回 `{ emotion, language, type: "audio_info" }`
- ✅ **Base64 编码**：官方支持 Data URL 格式

---

## 4.3 Agent 调用流程（文本 → Agent 回复）

### 4.3.1 完整时序图（设计目标）

```
Inbound Handler        OpenClaw SDK         Gateway Core        Agent Core
       │                   │                    │                   │
       │  构建 MessageContext                  │                   │
       │  { from, to, text, channel, ... }     │                   │
       │                   │                    │                   │
       │  dispatchReplyFromConfig()            │                   │
       │ ────────────────> │                    │                   │
       │                   │  构建 Agent 请求   │                   │
       │                   │ ─────────────────> │                   │
       │                   │                    │  调用 LLM         │
       │                   │                    │ ────────────────> │
       │                   │                    │                   │
       │                   │  流式响应          │                   │
       │                   │ <───────────────── │                   │
       │                   │  { delta: "你" }   │                   │
       │                   │                    │                   │
       │  dispatcher 回调  │                    │                   │
       │ <──────────────── │                    │                   │
       │  发送 TTS 请求     │                    │                   │
       │ ──────────────────────────────────────────────────────────
       │                   │                    │                   │
       │                   │  { delta: "好" }   │                   │
       │ <──────────────── │                    │                   │
       │  发送 TTS 请求     │                    │                   │
       │                   │                    │                   │
       │                   │  { done: true }    │                   │
       │ <──────────────── │                    │                   │
       │                   │                    │                   │
```

### 4.3.2 当前问题

**⚠️ 关键缺失**：当前代码中**没有实现** Agent 调用！

```typescript
// packages/server/src/messaging/inbound/handler.ts
// ❌ 当前代码：TODO 占位符
runtime: {
  deliver: async (ctx) => {
    // TODO: Deliver to Gateway (Step 5)
    log.info(`Gateway delivery: from=${ctx.from}, text="${ctx.text}"`);
  },
}
```

**需要实现**：
```typescript
// ✅ 正确实现（参考 openclaw-lark）
import { pluginRuntime } from '../index';  // 保存的 api.runtime

await pluginRuntime.channel.reply.dispatchReplyFromConfig({
  ctx: messageContext,
  cfg: config,
  dispatcher: createVoiceAgentDispatcher(ws),
  replyOptions: {
    abortSignal: abortController.signal,
  },
});
```

### 4.3.3 待验证

- [ ] **runtime 保存**：`packages/server/src/index.ts` 中是否有保存 `api.runtime`？
- [ ] **dispatcher 创建**：如何创建适合 voice-agent 的 dispatcher？
- [ ] **流式处理**：如何接收 Agent 的流式响应并逐块发送给 TTS？
- [ ] **会话隔离**：多用户并发时如何保证会话不混淆？

---

## 4.4 TTS 播放流程（Agent 回复 → 浏览器播放）

### 4.4.1 完整时序图

```
Plugin (Outbound)       TTS Client        阿里百炼 API       浏览器
       │                   │                  │                │
       │  接收 Agent 回复  │                  │                │
       │  text: "你好，有什么可以帮助你的？"                   │
       │                   │                  │                │
       │  调用 synthesize()                  │                │
       │ ────────────────> │  Python 脚本     │                │
       │                   │ ───────────────> │                │
       │                   │                  │                │
       │                   │  调用 dashscope SDK              │
       │                   │ ───────────────────────────────> │
       │                   │                  │                │
       │                   │  返回 PCM 音频   │                │
       │                   │ <─────────────────────────────── │
       │                   │  保存到 /tmp/tts-xxx.wav        │
       │ <─────────────── │                  │                │
       │  Uint8Array       │                  │                │
       │                   │                  │                │
       │  转换为 Base64    │                  │                │
       │                   │                  │                │
       │  WebSocket 发送音频                  │                │
       │ ───────────────────────────────────────────────────> │
       │                   │                  │  {             │
       │                   │                  │    type: "agent_audio",
       │                   │                  │    data: {     │
       │                   │                  │      audio: "base64...",
       │                   │                  │      isChunk: false
       │                   │                  │    }           │
       │                   │                  │  }             │
       │                   │                  │                │
       │                   │                  │  AudioContext 播放
       │                   │                  │ <──────────── │
```

### 4.4.2 关键代码

**TTS 调用**：
```typescript
// packages/server/src/tts/client.ts
async synthesize(text: string): Promise<TTSResult> {
  const scriptPath = path.join(__dirname, 'tts-synthesize.py');
  const tempOutput = `/tmp/tts-${Date.now()}.wav`;

  const { stdout, stderr } = await execAsync(
    `ALI_BAILIAN_API_KEY=${this.apiKey} python3 ${scriptPath} ` +
    `"${text}" "${this.model}" "${this.voice}" "${tempOutput}"`
  );

  const audioData = fs.readFileSync(tempOutput);
  return { audioData: new Uint8Array(audioData) };
}
```

**音频发送**：
```typescript
// packages/server/src/messaging/outbound/outbound.ts
sendText: async (params) => {
  const ws = getUserConnection(params.to);
  
  // ❌ 问题：只发送文本，没有触发 TTS
  ws.send(JSON.stringify({
    type: 'agent_text',
    data: { text: params.text },
  }));
  
  // ✅ 需要添加：触发 TTS 并发送音频
  // const ttsResult = await ttsClient.synthesize(params.text);
  // ws.send(JSON.stringify({
  //   type: 'agent_audio',
  //   data: { audio: ttsResult.audioData.toString('base64') },
  // }));
}
```

### 4.4.3 待验证

- [ ] **Python 脚本**：`tts-synthesize.py` 是否存在？功能是否完整？
- [ ] **TTS 触发时机**：收到 Agent 回复后立即触发？还是等完整回复？
- [ ] **流式 TTS**：是否支持边接收 Agent 回复边合成？（降低延迟）
- [ ] **音频播放**：浏览器如何播放流式音频块？（需查 `packages/webui/`）
- [ ] **并发处理**：多个用户同时收到回复时如何处理？

---

## 4.5 错误处理流程

### 4.5.1 错误类型与处理

| 错误类型 | 可能原因 | 处理策略 | 用户提示 |
|---------|---------|---------|---------|
| **WebSocket 连接失败** | 服务器未启动/端口被占用 | 自动重连（3 次） | "连接失败，正在重试..." |
| **麦克风权限拒绝** | 用户拒绝/浏览器限制 | 提示用户授权 | "请允许麦克风权限" |
| **STT API 失败** | 网络问题/API 限流 | 重试 2 次 → 降级 | "语音识别失败，请重试" |
| **Agent 调用失败** | Gateway 未启动/配置错误 | 记录日志，返回错误 | "服务暂时不可用" |
| **TTS API 失败** | 网络问题/API 限流 | 返回文本，跳过 TTS | "正在显示文字回复" |
| **音频播放失败** | 浏览器不支持/解码错误 | 记录日志 | 无明显提示 |

### 4.5.2 错误消息格式

```typescript
// 服务端发送错误
ws.send(JSON.stringify({
  type: 'error',
  data: {
    code: 'STT_FAILED',
    message: '语音识别失败，请重试',
    details: {  // 可选，开发环境
      error: 'Network timeout',
      retryCount: 2,
    },
  },
}));
```

### 4.5.3 待验证

- [ ] **重试机制**：当前代码是否有实现重试？（需查 STT/TTS client）
- [ ] **错误码定义**：是否有统一的错误码枚举？（需查 `packages/server/src/types.ts`）
- [ ] **降级策略**：TTS 失败时是否返回文本？（需查 outbound handler）

---

## 4.6 完整端到端流程（汇总）

### 4.6.1 泳道图

```
┌─────────────┬──────────────┬─────────────┬──────────────┬─────────────┐
│   用户      │   浏览器     │  WebSocket  │   Plugin     │   Agent     │
├─────────────┼──────────────┼─────────────┼──────────────┼─────────────┤
│ 点击录音    │              │             │              │             │
│ ──────────> │ 开始录音     │             │              │             │
│             │ 发送音频流  ─┼────────────>│ 累积音频     │             │
│ 停止录音    │              │             │              │             │
│ ──────────> │ 发送 isFinal ┼────────────>│ 调用 STT     │             │
│             │              │             │ ────────────>│             │
│             │              │             │              │             │
│             │              │             │ 返回文本     │             │
│             │              │             │ <─────────── │             │
│             │              │             │              │             │
│             │              │             │ 调用 Agent   │             │
│             │              │             │ ────────────>│             │
│             │              │             │              │ 处理请求    │
│             │              │             │              │ 返回回复    │
│             │              │             │ <─────────── │             │
│             │              │             │              │             │
│             │              │             │ 调用 TTS     │             │
│             │              │             │ ────────────>│             │
│             │              │             │ 返回音频     │             │
│             │              │             │ <─────────── │             │
│             │              │             │              │             │
│             │              │ 发送音频   ─┼────────────> │             │
│             │ 播放音频    <┼─────────────│              │             │
│ 听到回复    <│              │             │              │             │
└─────────────┴──────────────┴─────────────┴──────────────┴─────────────┘
```

### 4.6.2 关键延迟点

| 阶段 | 预估延迟 | 优化空间 |
|------|---------|---------|
| 录音 → 发送 | ~100ms (100ms 分块) | 可降至 50ms |
| STT 识别 | ~500ms (短文本) | 流式 STT 可降低 |
| Agent 响应 | ~1-3s (取决于 LLM) | 无法优化 |
| TTS 合成 | ~500ms (短文本) | 流式 TTS 可降低 |
| 音频播放 | ~50ms | 已优化 |
| **总计** | **~2-5s** | **流式可降至 ~1-2s** |

### 4.6.3 待验证

- [ ] **实际延迟**：端到端延迟是否真的在 2-5s？（需实测）
- [ ] **延迟瓶颈**：哪个阶段最慢？（需性能分析）
- [ ] **流式优化**：是否值得实现流式 STT/TTS？（需成本评估）

---

**第四部分 完**

---

*下一步：第五部分 - OpenClaw Channel Plugin 集成*

---

# 第五部分：OpenClaw Channel Plugin 集成

**说明**：本节详细说明如何正确实现 OpenClaw Channel Plugin 集成，参考 openclaw-lark 的实现模式。

---

## 5.1 Plugin 注册流程

### 5.1.1 完整注册流程

```
OpenClaw Gateway 启动
        ↓
扫描插件目录 (~/.openclaw/extensions/)
        ↓
发现 voice-agent 插件
        ↓
读取 openclaw.plugin.json
        ↓
验证 configSchema
        ↓
加载插件模块 (index.ts)
        ↓
调用 register(api)
        ↓
保存 api.runtime ← 关键步骤！
        ↓
注册 Channel (voice-agent)
        ↓
插件注册完成
```

### 5.1.2 关键代码：index.ts

**当前问题**：需要添加 `api.runtime` 保存逻辑

```typescript
// packages/server/src/index.ts
import type { PluginAPI } from 'openclaw/plugin-sdk';
import { voiceAgentPlugin } from './channel/plugin';

// ★ 关键：保存 runtime 供后续调用 Agent
let pluginRuntime: PluginAPI['runtime'] | null = null;

export function getRuntime(): PluginAPI['runtime'] {
  if (!pluginRuntime) {
    throw new Error('Plugin runtime not initialized');
  }
  return pluginRuntime;
}

export default {
  id: 'voice-agent',
  name: 'Voice Agent',
  description: 'Browser-based voice interaction channel',
  configSchema: {
    type: 'object',
    additionalProperties: false,
    properties: {
      enabled: { type: 'boolean', default: true },
      bailian: {
        type: 'object',
        properties: {
          apiKey: { type: 'string' },
          sttModel: { type: 'string', default: 'qwen3-asr-flash' },
          ttsModel: { type: 'string', default: 'qwen3-tts-instruct-flash' },
          ttsVoice: { type: 'string', default: 'Cherry' },
        },
      },
      serve: {
        type: 'object',
        properties: {
          port: { type: 'integer', default: 8765 },
          path: { type: 'string', default: '/voice-agent/stream' },
        },
      },
    },
  },
  
  register(api: PluginAPI) {
    // ★ 关键步骤：保存 runtime
    pluginRuntime = api.runtime;
    
    // 注册 Channel
    api.registerChannel({ plugin: voiceAgentPlugin });
    
    // 可选：注册 CLI 命令、HTTP 路由等
    // api.registerCli(...);
    // api.registerHttpRoute(...);
  },
};
```

### 5.1.3 与 openclaw-lark 对比

```typescript
// openclaw-lark/index.js (参考实现)
import { LarkClient } from './src/core/lark-client';

export default {
  id: 'openclaw-lark',
  register(api) {
    // ★ 同样的模式：保存 runtime
    LarkClient.setRuntime(api.runtime);
    
    // 注册 Channel
    api.registerChannel({ plugin: feishuPlugin });
    
    // 注册工具、命令等
    registerOapiTools(api);
    registerCommands(api);
  },
};
```

**结论**：模式完全一致，voice-agent 需要添加相同的 runtime 保存逻辑。

---

## 5.2 Agent 调用实现

### 5.2.1 正确的 Agent 调用方式

**参考 openclaw-lark 的实现**：

```typescript
// packages/server/src/messaging/inbound/handler.ts
import { getRuntime } from '../index';  // 导入保存的 runtime

/**
 * 调用 OpenClaw Agent 处理消息
 */
async function dispatchToAgent(
  messageContext: MessageContext,
  config: VoiceAgentConfig,
  ws: WebSocket,
  sessionId: string
): Promise<void> {
  const runtime = getRuntime();  // 获取保存的 runtime
  
  // 创建 dispatcher 接收 Agent 流式回复
  const { dispatcher, replyOptions, markDispatchIdle, markFullyComplete } = 
    createVoiceAgentDispatcher(ws, sessionId);
  
  // ★ 关键调用：dispatchReplyFromConfig
  try {
    const { queuedFinal, counts } = await runtime.channel.reply.dispatchReplyFromConfig({
      ctx: messageContext,
      cfg: config,
      dispatcher,
      replyOptions: {
        ...replyOptions,
        abortSignal: new AbortController().signal,
      },
    });
    
    // 等待所有消息发送完成
    await dispatcher.waitForIdle();
    markFullyComplete();
    markDispatchIdle();
    
    log.info(`Agent dispatch complete (replies=${counts.final})`);
  } catch (error) {
    log.error(`Agent dispatch failed: ${error}`);
    throw error;
  }
}
```

### 5.2.2 Dispatcher 创建

**需要实现 voice-agent 专用的 dispatcher**：

```typescript
// packages/server/src/messaging/inbound/dispatcher.ts
import { WebSocket } from 'ws';
import { TTSClient } from '../tts/client';

/**
 * 创建 Voice Agent 专用的 Dispatcher
 * 
 * 功能：
 * 1. 接收 Agent 流式文本回复
 * 2. 逐块调用 TTS 合成音频
 * 3. 通过 WebSocket 发送音频给浏览器
 */
export function createVoiceAgentDispatcher(
  ws: WebSocket,
  sessionId: string
) {
  const ttsClient = new TTSClient({ apiKey: '...' });
  let isIdle = false;
  let isFullyComplete = false;
  
  // Dispatcher 回调：接收 Agent 回复
  const dispatcher = async (reply) => {
    const { final, text } = reply;
    
    if (text) {
      // 发送文本（用于字幕显示）
      ws.send(JSON.stringify({
        type: 'agent_text',
        data: { text, isFinal: final },
      }));
      
      // 调用 TTS 合成音频
      const ttsResult = await ttsClient.synthesize(text);
      
      // 发送音频
      ws.send(JSON.stringify({
        type: 'agent_audio',
        data: {
          audio: ttsResult.audioData.toString('base64'),
          isChunk: !final,
        },
      }));
    }
    
    if (final) {
      isFullyComplete = true;
    }
  };
  
  // 回复选项
  const replyOptions = {
    // 配置项（参考 openclaw-lark）
  };
  
  // 状态标记
  const markDispatchIdle = () => { isIdle = true; };
  const markFullyComplete = () => { isFullyComplete = true; };
  
  return {
    dispatcher,
    replyOptions,
    markDispatchIdle,
    markFullyComplete,
    waitForIdle: async () => {
      // 等待 dispatcher 空闲
      while (!isIdle) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    },
  };
}
```

### 5.2.3 完整调用流程

```
Inbound Handler
       ↓
收到 STT 文本 ("你好")
       ↓
构建 MessageContext
{ from: "user123", to: "voice-agent", text: "你好", channel: "voice-agent" }
       ↓
调用 dispatchToAgent()
       ↓
获取 runtime (api.runtime)
       ↓
创建 Voice Agent Dispatcher
       ↓
调用 runtime.channel.reply.dispatchReplyFromConfig()
       ↓
OpenClaw Gateway Core
       ↓
Agent Core (LLM)
       ↓
流式返回："你好" → "有" → "什么" → "可以" → "帮" → "你" → "的" → "？"
       ↓
Dispatcher 逐块接收
       ↓
每块调用 TTS 合成
       ↓
通过 WebSocket 发送音频
       ↓
浏览器播放
```

---

## 5.3 配置管理

### 5.3.1 Plugin 配置 Schema

**当前实现**（已正确）：

```json
// packages/server/openclaw.plugin.json
{
  "configSchema": {
    "type": "object",
    "additionalProperties": false,
    "properties": {
      "enabled": { "type": "boolean", "default": true },
      "bailian": {
        "type": "object",
        "properties": {
          "apiKey": { "type": "string" },
          "sttModel": { "type": "string", "default": "qwen3-asr-flash" },
          "ttsModel": { "type": "string", "default": "qwen3-tts-instruct-flash" },
          "ttsVoice": { "type": "string", "default": "Cherry" }
        }
      },
      "serve": {
        "type": "object",
        "properties": {
          "port": { "type": "integer", "default": 8765 },
          "path": { "type": "string", "default": "/voice-agent/stream" }
        }
      }
    }
  }
}
```

### 5.3.2 配置文件位置

```
~/.openclaw/config.json
{
  "plugins": {
    "entries": {
      "voice-agent": {
        "enabled": true,
        "config": {
          "bailian": {
            "apiKey": "sk-xxx"
          },
          "serve": {
            "port": 8765
          }
        }
      }
    }
  },
  "channels": {
    "voice-agent": {
      // Channel 特定配置
    }
  }
}
```

### 5.3.3 与 openclaw-lark 对比

| 配置项 | openclaw-lark | voice-agent | 说明 |
|--------|---------------|-------------|------|
| **API Key** | `lark.appId` / `lark.appSecret` | `bailian.apiKey` | 认证凭证 |
| **服务端口** | `webhookPort` (可选) | `serve.port` (必需) | WebSocket 监听端口 |
| **模型配置** | 无（使用飞书默认） | `sttModel` / `ttsModel` | STT/TTS 模型选择 |
| **配置位置** | `channels.feishu` | `channels.voice-agent` | 统一配置结构 |

---

## 5.4 生命周期管理

### 5.4.1 Plugin 生命周期

```
OpenClaw Gateway 启动
        ↓
调用 plugin.register(api)
        ↓
保存 api.runtime
        ↓
注册 Channel
        ↓
Gateway 调用 gateway.startAccount()
        ↓
启动 WebSocket Server (端口 8765)
        ↓
Plugin 运行中...
        ↓
接收浏览器连接
        ↓
处理消息（STT → Agent → TTS）
        ↓
Gateway 关闭或重启
        ↓
调用 gateway.stopAccount()
        ↓
关闭 WebSocket Server
        ↓
清理会话
        ↓
Plugin 停止
```

### 5.4.2 生命周期代码

```typescript
// packages/server/src/channel/plugin.ts
export const voiceAgentPlugin: ChannelPlugin = {
  id: 'voice-agent',
  
  gateway: {
    // Gateway 启动时调用
    startAccount: async (ctx) => {
      log.info('Starting voice agent server...');
      
      const config = ctx.cfg as VoiceAgentConfig;
      
      // 创建并启动 WebSocket Server
      wsServer = new VoiceAgentWebSocketServer({
        port: config.serve?.port ?? 8765,
        path: config.serve?.path ?? '/voice-agent/stream',
        config,
      }, sessionManager);
      
      log.info(`Voice agent server started on port ${config.serve?.port ?? 8765}`);
      
      return {
        port: config.serve?.port ?? 8765,
      };
    },
    
    // Gateway 停止时调用
    stopAccount: async (ctx) => {
      log.info('Stopping voice agent server...');
      
      if (wsServer) {
        wsServer.close();
        wsServer = null;
      }
      
      if (sessionManager) {
        sessionManager.destroy();
        sessionManager = null;
      }
      
      log.info('Voice agent server stopped');
    },
  },
};
```

### 5.4.3 与 openclaw-lark 对比

```javascript
// openclaw-lark/src/channel/plugin.js (参考)
gateway: {
  startAccount: async (ctx) => {
    const { monitorFeishuProvider } = await import('./monitor.js');
    return monitorFeishuProvider({
      config: ctx.cfg,
      runtime: ctx.runtime,
      abortSignal: ctx.abortSignal,
      accountId: ctx.accountId,
    });
  },
  
  stopAccount: async (ctx) => {
    LarkClient.clearCache(ctx.accountId);
  },
}
```

**对比结论**：
- ✅ 生命周期钩子一致（startAccount / stopAccount）
- ✅ 参数结构一致（ctx.cfg, ctx.runtime, ctx.abortSignal）
- ✅ 返回值一致（返回服务信息）

---

## 5.5 关键差异总结

### 5.5.1 voice-agent vs openclaw-lark

| 方面 | openclaw-lark | voice-agent | 说明 |
|------|---------------|-------------|------|
| **消息来源** | 飞书 Webhook 推送 | WebSocket Server 监听 | 被动 vs 主动 |
| **消息格式** | 飞书事件格式 | 自定义 JSON 格式 | 标准化 vs 自定义 |
| **输入处理** | 直接文本 | 音频 → STT → 文本 | 无需 STT vs 需要 STT |
| **输出处理** | 直接发送文本 | 文本 → TTS → 音频 | 无需 TTS vs 需要 TTS |
| **Dispatcher** | 飞书卡片/文本 | TTS 音频流 | 文本发送 vs 音频发送 |
| **配置复杂度** | 中等（appId/secret） | 简单（apiKey） | 企业认证 vs API Key |

### 5.5.2 实现复杂度对比

```
openclaw-lark:
  消息接收 → 解析飞书事件 → dispatchReplyFromConfig → 发送飞书消息
  (4 步，纯文本)

voice-agent:
  消息接收 → WebSocket 音频 → STT → dispatchReplyFromConfig → TTS → WebSocket 音频
  (6 步，音频处理)
```

**结论**：voice-agent 实现更复杂，因为需要处理音频流和 STT/TTS。

---

## 5.6 待实现清单

### 5.6.1 高优先级（阻塞功能）

- [ ] **runtime 保存**：在 `index.ts` 中添加 `api.runtime` 保存逻辑
- [ ] **Agent 调用**：在 `inbound/handler.ts` 中实现 `dispatchToAgent()`
- [ ] **Dispatcher 创建**：实现 `createVoiceAgentDispatcher()`
- [ ] **TTS 触发**：在 Dispatcher 中集成 TTS 调用

### 5.6.2 中优先级（影响体验）

- [ ] **流式处理**：支持边接收 Agent 回复边调用 TTS
- [ ] **错误处理**：Agent 调用失败时的降级策略
- [ ] **会话隔离**：多用户并发时的会话管理

### 5.6.3 低优先级（优化项）

- [ ] **CLI 命令**：注册 voice-agent 专用 CLI 命令
- [ ] **HTTP 路由**：提供 REST API 用于调试
- [ ] **监控指标**：暴露 Prometheus 指标

---

**第五部分 完**

---

*下一步：第六部分 - UI 交互设计详解*

---

# 第六部分：UI 交互设计详解

**说明**：本节详细说明 WebUI 的组件设计、状态管理和用户交互流程。

---

## 6.1 UI 组件结构

### 6.1.1 组件树

```
App (主应用容器)
├── VoiceLayout (语音交互布局)
│   ├── StatusIndicator (状态指示器)
│   │   └── 显示：离线/连接中/已连接/错误
│   ├── VoiceCard (语音卡片)
│   │   ├── VoiceButton (录音按钮)
│   │   │   └── 支持点击/长按，带脉冲动画
│   │   ├── Waveform (波形动画)
│   │   │   └── 5-7 根动态条形，随音量变化
│   │   └── Transcript (字幕显示)
│   │       └── 实时显示 STT 结果和 Agent 回复
│   └── ConnectionState (连接信息)
│       └── 显示 WebSocket 连接状态
└── TypingEffect (打字机效果)
    └── Agent 回复的打字机效果
```

### 6.1.2 核心组件职责

| 组件 | 文件位置 | 职责 | 状态来源 |
|------|----------|------|---------|
| `App` | `packages/webui/src/App.tsx` | 主应用容器，状态协调 | voiceStore |
| `VoiceButton` | `packages/webui/src/components/VoiceButton.tsx` | 录音控制，动画 | 本地 + voiceStore |
| `Waveform` | `packages/webui/src/components/Waveform.tsx` | 音频波形可视化 | audioLevel (本地) |
| `Transcript` | `packages/webui/src/components/Transcript.tsx` | 字幕显示 | transcript (voiceStore) |
| `StatusIndicator` | `packages/webui/src/components/StatusIndicator.tsx` | 状态指示器 | connectionStatus (voiceStore) |

---

## 6.2 状态管理

### 6.2.1 Zustand Store 设计

```typescript
// packages/webui/src/store/voiceStore.ts
interface VoiceState {
  // 连接状态
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  ws: WebSocket | null;
  
  // 录音状态
  isRecording: boolean;
  audioLevel: number;  // 0-1，用于波形动画
  
  // 播放状态
  isPlaying: boolean;
  audioQueue: AudioChunk[];
  
  // 字幕
  transcript: string;
  isTranscriptFinal: boolean;
  
  // 错误
  error: string | null;
  
  // 动作
  connect: () => Promise<void>;
  disconnect: () => void;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  updateTranscript: (text: string, isFinal: boolean) => void;
  playAudio: (base64: string) => void;
}
```

### 6.2.2 状态流转

```
初始状态
  ↓
connect()
  ↓
connectionStatus: 'connecting'
  ↓
WebSocket 连接成功
  ↓
connectionStatus: 'connected'
  ↓
startRecording()
  ↓
isRecording: true
  ↓
stopRecording()
  ↓
isRecording: false
  ↓
接收 STT 结果
  ↓
updateTranscript(text, false) → updateTranscript(text, true)
  ↓
接收 TTS 音频
  ↓
playAudio(base64) → isPlaying: true → isPlaying: false
```

---

## 6.3 用户交互流程

### 6.3.1 完整交互流程

```
用户打开页面
       ↓
自动连接 WebSocket
       ↓
显示"连接中..."
       ↓
连接成功
       ↓
显示"点击录音"按钮 (绿色)
       ↓
用户点击录音按钮
       ↓
请求麦克风权限
       ↓
用户允许
       ↓
开始录音 + 发送音频流
       ↓
按钮变红 + 波形动画
       ↓
显示"录音中..."
       ↓
用户点击停止
       ↓
停止录音 + 发送 isFinal
       ↓
显示"处理中..." (蓝色)
       ↓
接收 STT 结果
       ↓
显示字幕 (草稿 → 最终)
       ↓
接收 TTS 音频
       ↓
显示"播放中..." (紫色) + 波形动画
       ↓
播放完成
       ↓
返回"点击录音"状态
```

### 6.3.2 异常处理流程

```
连接失败
       ↓
显示"连接失败，点击重试" (红色)
       ↓
用户点击重试
       ↓
重新连接 (最多 3 次)
       ↓
仍失败 → 显示错误信息

麦克风权限拒绝
       ↓
显示"请允许麦克风权限" + 引导链接

STT 失败
       ↓
显示"语音识别失败，请重试"

TTS 失败
       ↓
降级显示文本回复
```

---

## 6.4 视觉设计规范

### 6.4.1 设计风格

**参考**：ChatGPT Voice Mode 风格

| 元素 | 设计规范 |
|------|---------|
| **主色调** | 深色背景 (#1A1A2E) + 渐变色（紫/蓝/青） |
| **录音按钮** | 圆形 (直径 80px)，带脉冲动画 |
| **波形** | 5-7 根动态条形，高度随音量变化 |
| **字幕** | 居中显示，白色文字 (#FFFFFF)，带淡入效果 |
| **状态指示器** | 小圆点 (直径 12px)，颜色随状态变化 |

### 6.4.2 状态颜色

| 状态 | 颜色 | 十六进制 | 说明 |
|------|------|---------|------|
| 离线 | 灰色 | #666666 | 未连接 |
| 连接中 | 黄色 | #FFC107 | 正在建立连接 |
| 已连接 | 绿色 | #4CAF50 | 可以录音 |
| 录音中 | 红色 | #F44336 | 正在录音 |
| 处理中 | 蓝色 | #2196F3 | STT/Agent 处理 |
| 播放中 | 紫色 | #9C27B0 | TTS 播放 |
| 错误 | 橙红色 | #FF5722 | 发生错误 |

### 6.4.3 响应式设计

| 断点 | 宽度 | 布局调整 |
|------|------|---------|
| Mobile | < 640px | 单列，大按钮 (直径 100px) |
| Tablet | 640px - 1024px | 居中卡片，最大宽度 400px |
| Desktop | > 1024px | 最大宽度 500px，居中显示 |

---

## 6.5 待确认

- [ ] **VoiceAgentClient 位置**：是独立类还是分散在 hooks 中？（需查 `packages/webui/src/`）
- [ ] **PCM 编码实现**：`encodeToPCM` 函数是否存在？（需查 `packages/webui/src/utils/audio.ts`）
- [ ] **音频播放**：如何播放流式音频块？（需查 `packages/webui/src/hooks/useAudioPlayer.ts`）

---

# 第七部分：技术实现细节

**说明**：本节说明关键技术决策、接口定义、数据格式和外部依赖。不包含具体实现代码。

---

## 7.1 WebSocket 协议

### 7.1.1 连接信息

| 项目 | 值 |
|------|-----|
| **URL** | `ws://localhost:8765/voice-agent/stream` |
| **协议** | WebSocket (RFC 6455) |
| **消息格式** | JSON |
| **编码** | UTF-8 |

### 7.1.2 客户端 → 服务端消息

**connect** - 建立连接
```json
{
  "type": "connect",
  "userId": "string"
}
```

**audio** - 发送音频
```json
{
  "type": "audio",
  "data": {
    "payload": "string (Base64 PCM)",
    "isFinal": "boolean",
    "sampleRate": "number (默认 16000)",
    "channels": "number (默认 1)"
  }
}
```

**control** - 控制命令
```json
{
  "type": "control",
  "action": "start" | "stop" | "interrupt" | "ping"
}
```

### 7.1.3 服务端 → 客户端消息

**status** - 状态更新
```json
{
  "type": "status",
  "state": "idle" | "listening" | "processing" | "speaking" | "error",
  "sessionId": "string"
}
```

**transcript** - STT 结果
```json
{
  "type": "transcript",
  "data": {
    "text": "string",
    "isFinal": "boolean"
  }
}
```

**agent_text** - Agent 文本回复
```json
{
  "type": "agent_text",
  "data": {
    "text": "string",
    "messageId": "string",
    "timestamp": "number"
  }
}
```

**agent_audio** - TTS 音频
```json
{
  "type": "agent_audio",
  "data": {
    "audio": "string (Base64 PCM)",
    "messageId": "string",
    "timestamp": "number",
    "isChunk": "boolean"
  }
}
```

**error** - 错误信息
```json
{
  "type": "error",
  "data": {
    "code": "string",
    "message": "string"
  }
}
```

---

## 7.2 音频格式

### 7.2.1 输入音频（浏览器 → 服务端）

| 属性 | 值 |
|------|-----|
| **格式** | PCM (脉冲编码调制) |
| **采样率** | 16000 Hz |
| **位深** | 16 bit |
| **声道** | 单声道 (mono) |
| **编码** | Base64 |
| **MIME 类型** | `audio/wav` |
| **数据 URL** | `data:audio/wav;base64,{base64Data}` |

### 7.2.2 输出音频（服务端 → 浏览器）

| 属性 | 值 |
|------|-----|
| **格式** | PCM (脉冲编码调制) |
| **采样率** | 24000 Hz (TTS 输出) |
| **位深** | 16 bit |
| **声道** | 单声道 (mono) |
| **编码** | Base64 |
| **MIME 类型** | `audio/wav` |

---

## 7.3 STT 集成

### 7.3.1 服务商

**阿里百炼 (DashScope)**
- API 端点：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 模型：`qwen3-asr-flash`
- 认证：API Key (Bearer Token)

### 7.3.2 接口定义

```typescript
interface STTClient {
  transcribe(audioBase64: string): Promise<STTResult>;
}

interface STTResult {
  text: string;
  language?: string;
  emotion?: string;
  confidence?: number;
}
```

### 7.3.3 依赖

- Node.js 包：`openai` (兼容模式)
- 环境变量：`ALI_BAILIAN_API_KEY`

---

## 7.4 TTS 集成

### 7.4.1 服务商

**阿里百炼 (DashScope)**
- 模型：`qwen3-tts-instruct-flash`
- 语音：`Cherry` (默认)
- 认证：API Key (Bearer Token)

### 7.4.2 特殊设计：Python 脚本调用

**原因**：Node.js dashscope 包不兼容，需要用 Python SDK。

**接口定义**：
```bash
# Python 脚本命令行接口
python3 tts-synthesize.py <text> <model> <voice> <output_path>
```

**参数**：
- `text`: 待合成文本 (字符串)
- `model`: TTS 模型 (如 `qwen3-tts-instruct-flash`)
- `voice`: 语音 (如 `Cherry`)
- `output_path`: 输出 WAV 文件路径

**输出**：
- WAV 文件 (PCM 24kHz 16bit mono)

### 7.4.3 依赖

- Python 3.x
- Python 包：`dashscope`
- 环境变量：`ALI_BAILIAN_API_KEY`

---

## 7.5 OpenClaw 集成

### 7.5.1 Plugin 注册

**入口文件**：`packages/server/src/index.ts`

**关键步骤**：
1. 保存 `api.runtime` (供后续调用 Agent)
2. 注册 Channel (`voice-agent`)
3. 导出 `getRuntime()` 函数

### 7.5.2 Agent 调用

**接口**：`api.runtime.channel.reply.dispatchReplyFromConfig()`

**参数**：
- `ctx`: MessageContext (消息上下文)
- `cfg`: VoiceAgentConfig (配置)
- `dispatcher`: 回复处理器 (接收流式回复)
- `replyOptions`: 回复选项

### 7.5.3 配置结构

```json
{
  "plugins": {
    "entries": {
      "voice-agent": {
        "enabled": true,
        "config": {
          "bailian": {
            "apiKey": "sk-xxx"
          },
          "serve": {
            "port": 8765
          }
        }
      }
    }
  }
}
```

---

## 7.6 外部依赖清单

### 7.6.1 Node.js 依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| `ws` | ^8.x | WebSocket 服务器 |
| `openai` | ^4.x | STT API 调用 (兼容模式) |
| `openclaw/plugin-sdk` | 内置 | Plugin SDK |

### 7.6.2 Python 依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| `dashscope` | 最新 | TTS API 调用 |

### 7.6.3 系统依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Node.js | >= 18 | 运行环境 |
| Python | >= 3.8 | TTS 脚本运行 |
| OpenSSL | 最新 | HTTPS/WSS 支持 |

---

## 7.7 技术决策记录

### 7.7.1 为什么用 WebSocket？

**决策**：WebSocket

**理由**：
1. 双向通信（音频上传 + 下载）
2. 低延迟（长连接，无需重复握手）
3. 浏览器支持好
4. 与 OpenClaw Gateway 一致

**备选方案**：
- HTTP Polling (延迟高，排除)
- Server-Sent Events (仅单向，排除)
- WebRTC (过度复杂，排除)

### 7.7.2 为什么用 PCM 16kHz？

**决策**：PCM 16kHz 16bit mono

**理由**：
1. STT 要求（阿里百炼支持）
2. 带宽友好（32 KB/s）
3. 处理简单（无需编解码）
4. TTS 兼容（输出格式一致）

### 7.7.3 为什么 TTS 用 Python 脚本？

**决策**：Python 脚本调用

**理由**：
1. Node.js dashscope 包不兼容
2. Python SDK 成熟稳定
3. 性能可接受（进程启动开销 ~100ms）

**备选方案**：
- HTTP 调用 TTS API（需自己处理认证，排除）
- 等待 Node.js SDK 更新（时间不确定，排除）

---

# 第八部分：现状 Gap 分析

**说明**：本节分析当前代码实现与目标状态的差距，明确需要完成的工作。

---

## 8.1 已完成功能

### 8.1.1 核心框架

| 功能 | 状态 | 文件位置 |
|------|------|---------|
| WebSocket Server | ✅ 完成 | `packages/server/src/websocket/server.ts` |
| Session Manager | ✅ 完成 | `packages/server/src/session/manager.ts` |
| STT Client | ✅ 完成 | `packages/server/src/stt/client.ts` |
| TTS Client | ✅ 完成 | `packages/server/src/tts/client.ts` |
| Channel Plugin | ✅ 完成 | `packages/server/src/channel/plugin.ts` |
| Inbound Handler | ✅ 完成 | `packages/server/src/messaging/inbound/handler.ts` |
| Outbound Handler | ✅ 完成 | `packages/server/src/messaging/outbound/outbound.ts` |

### 8.1.2 WebUI

| 功能 | 状态 | 文件位置 |
|------|------|---------|
| 录音功能 | ✅ 完成 | `packages/webui/src/hooks/useRecorder.ts` |
| 状态管理 | ✅ 完成 | `packages/webui/src/store/voiceStore.ts` |
| UI 组件 | ✅ 完成 | `packages/webui/src/components/` |
| 主应用 | ✅ 完成 | `packages/webui/src/App.tsx` |

### 8.1.3 测试验证

| 测试 | 状态 | 说明 |
|------|------|------|
| STT API | ✅ 通过 | TTS→STT 闭环测试 3/3 完全匹配 |
| TTS API | ✅ 通过 | 平均耗时 838ms |
| STT+TTS 闭环 | ✅ 通过 | 总平均耗时 1682ms |

---

## 8.2 核心功能缺失

### 8.2.1 Agent 集成（🔴 高优先级）

**问题**：代码中没有调用 OpenClaw Agent！

**缺失内容**：
1. ❌ `index.ts` 中未保存 `api.runtime`
2. ❌ `inbound/handler.ts` 中 `runtime.deliver` 是 TODO 占位符
3. ❌ 未实现 `createVoiceAgentDispatcher()`
4. ❌ 未调用 `dispatchReplyFromConfig()`

**影响**：
- 用户语音 → STT → **无 Agent 处理** → 无回复
- 完整流程中断，无法实现核心功能

**修复方案**：
1. 在 `index.ts` 中添加 runtime 保存逻辑
2. 在 `inbound/handler.ts` 中实现 Agent 调用
3. 创建 Voice Agent Dispatcher
4. 集成 TTS 到 Dispatcher

**预计工作量**：4-6 小时

---

### 8.2.2 TTS 触发（🔴 高优先级）

**问题**：Outbound Handler 只发送文本，未触发 TTS

**缺失内容**：
1. ❌ `sendText()` 未调用 TTS
2. ❌ 无 `sendAudio()` 方法
3. ❌ Python 脚本 `tts-synthesize.py` 需确认是否存在

**影响**：
- Agent 回复只能显示文本，无法播放语音
- 用户体验不完整

**修复方案**：
1. 在 Outbound Handler 中集成 TTS 调用
2. 实现 `sendAudio()` 方法
3. 确认/创建 Python 脚本

**预计工作量**：2-3 小时

---

### 8.2.3 错误处理（🟡 中优先级）

**问题**：缺少完善的错误处理机制

**缺失内容**：
1. ❌ STT 失败无重试
2. ❌ TTS 失败无降级
3. ❌ WebSocket 断线无重连
4. ❌ 错误码未统一

**影响**：
- 用户体验差（失败无提示）
- 系统稳定性低

**修复方案**：
1. 实现重试机制（STT/TTS 各 2 次重试）
2. TTS 失败降级显示文本
3. WebSocket 自动重连（最多 3 次）
4. 定义统一错误码

**预计工作量**：3-4 小时

---

## 8.3 待确认事项

### 8.3.1 代码文件

| 文件 | 状态 | 说明 |
|------|------|------|
| `packages/server/src/index.ts` | ❓ 待确认 | 是否有 runtime 保存逻辑 |
| `packages/server/src/tts/tts-synthesize.py` | ❓ 待确认 | Python 脚本是否存在 |
| `packages/webui/src/lib/VoiceAgentClient.ts` | ❓ 待确认 | 是否有独立客户端类 |
| `packages/webui/src/utils/audio.ts` | ❓ 待确认 | PCM 编码函数是否存在 |

### 8.3.2 功能验证

| 功能 | 状态 | 说明 |
|------|------|------|
| WebSocket 连接 | ❓ 待实测 | 浏览器能否成功连接 |
| 录音功能 | ❓ 待实测 | 麦克风权限 + 录音 |
| STT 识别 | ✅ 已验证 | API 测试通过 |
| Agent 调用 | ❌ 未实现 | 核心缺失 |
| TTS 播放 | ❓ 待实测 | Python 脚本 + 播放 |

---

## 8.4 完成度评估

| 模块 | 完成度 | 说明 |
|------|-------|------|
| **WebSocket Server** | 90% | 连接管理完成，缺错误处理 |
| **STT Client** | 90% | API 调用完成，缺重试机制 |
| **TTS Client** | 70% | Python 脚本待确认 |
| **Channel Plugin** | 80% | 框架完成，缺 runtime 保存 |
| **Inbound Handler** | 60% | 消息处理完成，缺 Agent 调用 |
| **Outbound Handler** | 50% | 文本发送完成，缺 TTS 触发 |
| **WebUI** | 80% | 组件完成，缺集成测试 |
| **整体可用** | **40%** | 核心功能（Agent 集成）缺失 |

---

# 第九部分：实施计划

**说明**：本节制定详细的实施时间表和优先级。

---

## 9.1 实施阶段

### Phase 1: 核心功能（立即执行）

**目标**：实现 Agent 集成，完成端到端流程

**任务**：
1. [ ] 在 `index.ts` 中添加 runtime 保存逻辑
2. [ ] 在 `inbound/handler.ts` 中实现 Agent 调用
3. [ ] 创建 `createVoiceAgentDispatcher()`
4. [ ] 在 Outbound Handler 中集成 TTS
5. [ ] 确认/创建 Python 脚本 `tts-synthesize.py`

**验收标准**：
- ✅ 用户说话 → STT → Agent → TTS → 播放 完整流程打通
- ✅ 端到端延迟 < 5s

**预计时间**：1 天

---

### Phase 2: 错误处理（Phase 1 完成后）

**目标**：提升系统稳定性

**任务**：
1. [ ] 实现 STT 重试机制（2 次重试）
2. [ ] 实现 TTS 降级（失败显示文本）
3. [ ] 实现 WebSocket 重连（最多 3 次）
4. [ ] 定义统一错误码
5. [ ] 添加用户友好提示

**验收标准**：
- ✅ API 失败有重试
- ✅ TTS 失败降级显示文本
- ✅ 错误提示清晰

**预计时间**：0.5 天

---

### Phase 3: 性能优化（Phase 2 完成后）

**目标**：降低延迟，提升体验

**任务**：
1. [ ] 流式 STT（边说话边识别）
2. [ ] 流式 TTS（边合成边播放）
3. [ ] 音频缓冲优化
4. [ ] 并发连接测试

**验收标准**：
- ✅ 首字延迟 < 2s
- ✅ 支持 10+ 并发用户

**预计时间**：1-2 天

---

### Phase 4: 文档与部署（Phase 3 完成后）

**目标**：完善文档，准备部署

**任务**：
1. [ ] 更新 README.md
2. [ ] 编写部署指南
3. [ ] 编写故障排查文档
4. [ ] 配置示例
5. [ ] 生产环境配置（HTTPS/WSS）

**验收标准**：
- ✅ 新人可按文档部署
- ✅ 常见问题有解答

**预计时间**：0.5 天

---

## 9.2 时间表

| 阶段 | 开始日期 | 结束日期 | 工作日 |
|------|---------|---------|-------|
| Phase 1: 核心功能 | D1 | D1 | 1 天 |
| Phase 2: 错误处理 | D2 | D2 上午 | 0.5 天 |
| Phase 3: 性能优化 | D2 下午 | D3 | 1.5 天 |
| Phase 4: 文档部署 | D4 | D4 | 0.5 天 |
| **总计** | | | **3.5 天** |

---

## 9.3 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Python 脚本不存在 | 中 | 高 | 准备备用方案（HTTP API 直接调用） |
| Agent 集成复杂度高 | 中 | 高 | 参考 openclaw-lark 实现 |
| STT/TTS 延迟过高 | 低 | 中 | 流式处理优化 |
| 并发性能不足 | 低 | 中 | 压力测试 + 优化 |

---

## 9.4 交付物清单

| 交付物 | 位置 | 状态 |
|--------|------|------|
| 需求分析报告 | `docs/REQUIREMENTS-ANALYSIS.md` | ✅ 完成 |
| 源代码 | `packages/server/`, `packages/webui/` | 🔄 进行中 |
| README | `README.md` | ❌ 待更新 |
| 部署指南 | `docs/DEPLOYMENT.md` | ❌ 待编写 |
| 故障排查 | `docs/TROUBLESHOOTING.md` | ❌ 待编写 |
| API 文档 | `docs/API.md` | ❌ 待编写 |

---

**文档 完**

---

## 文档版本历史

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| 1.0 | 2026-03-16 | 羲和 | 初稿完成（9 部分） |

---

## 相关文档

| 文档 | 位置 | 说明 |
|------|------|------|
| **需求分析报告** | `docs/REQUIREMENTS-ANALYSIS.md` | 本文档（9 部分） |
| **交接文档** | `HANDOVER.md` | 详细交接指南 |
| **可行性分析** | `docs/可行性分析与方案对比.md` | 技术方案对比 |
| **官方文档调研** | `docs/官方文档调研.md` | STT/TTS API 调研 |
| **详细设计** | `docs/详细设计文档.md` | 技术详细设计 |

---

**最后更新**: 2026-03-16  
**文档版本**: 1.0  
**状态**: 初稿完成，待实施验证
