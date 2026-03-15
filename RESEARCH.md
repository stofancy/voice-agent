# Voice Agent 项目调研报告

**创建日期**: 2026-03-15  
**作者**: 羲和  
**状态**: 调研阶段

---

## 1. 项目背景

### 1.1 目标

为 OpenClaw 开发一个 Voice Agent Channel 插件，支持浏览器端语音交互。

### 1.2 核心需求

| 需求 | 优先级 | 说明 |
|------|--------|------|
| 语音指令 + 语音回复 | P0 | 用户说话 → STT → LLM → TTS → 播放 |
| 浏览器端 | P0 | WebSocket 连接，HTML/JS 客户端 |
| 流式输入/输出 | P0 | 支持实时 STT/TTS |
| 长期：实时对话 | P1 | 全双工、可打断 |

---

## 2. 现有资产分析

### 2.1 Qwen3-Realtime-SDK

**位置**: `~/workspaces/qwen3-realtime-sdk/`

**能力**:
- ✅ 百炼实时语音 API 封装
- ✅ WebSocket 服务器示例
- ✅ 浏览器客户端示例
- ✅ 端到端延迟 600-800ms

**架构**:
```
浏览器 (WebSocket) → Python WebSocket 服务器 → 百炼 Realtime API
```

**核心文件**:
```
qwen3-realtime-sdk/
├── qwen3_realtime/
│   ├── client.py        # 核心客户端
│   ├── config.py        # 配置类
│   ├── callback.py      # 回调接口
│   └── types.py         # 类型定义
├── examples/
│   └── websocket_server.py  # WebSocket 服务器
```

**API Key**: `sk-your-api-key-here`

---

## 3. 技术方案选择

### 3.1 方案对比

道友提出了使用两个独立模型：
- **STT**: `qwen3-asr-flash`
- **TTS**: `qwen3-tts-instruct-flash`

但现有 SDK 使用的是：
- **Realtime**: `qwen3-omni-flash-realtime`（端到端）

| 方案 | 模型 | 优点 | 缺点 |
|------|------|------|------|
| **方案 A** | Realtime 端到端 | 简单，已有 SDK，延迟低 | 灵活性较低 |
| **方案 B** | 独立 STT+TTS | 灵活，可独立控制 | 复杂度高，延迟可能更高 |

### 3.2 推荐方案

**推荐：方案 A（Realtime 端到端）**

**理由**:
1. 已有完整 SDK，无需重新开发
2. 端到端延迟更低（600-800ms）
3. 自动 VAD，自动流式处理
4. 简化实现，快速验证

**后续可扩展**: 如果需要更灵活的控制，可以升级到方案 B。

---

## 4. OpenClaw 集成架构

### 4.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Voice Agent Channel                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐                                           │
│  │   Browser    │                                           │
│  │  (HTML/JS)   │                                           │
│  └──────┬───────┘                                           │
│         │ WebSocket                                          │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        OpenClaw Voice Agent Plugin                    │   │
│  │                                                       │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌───────────┐ │   │
│  │  │  WebSocket  │───►│   Session   │───►│  Gateway  │ │   │
│  │  │   Server    │    │   Manager   │    │   RPC     │ │   │
│  │  └─────────────┘    └─────────────┘    └─────┬─────┘ │   │
│  │                                               │       │   │
│  └───────────────────────────────────────────────┼───────┘   │
│                                                  │           │
│                      ┌───────────────────────────┘           │
│                      │                                        │
│                      ▼                                        │
│         ┌────────────────────────┐                           │
│         │  Qwen3-Realtime-SDK    │                           │
│         │  (复用现有)            │                           │
│         └───────────┬────────────┘                           │
│                     │                                        │
│                     ▼                                        │
│         ┌────────────────────────┐                           │
│         │  百炼 Realtime API      │                           │
│         │  qwen3-omni-flash      │                           │
│         └────────────────────────┘                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 数据流

```
1. 用户说话
   浏览器 → WebSocket → Voice Agent Plugin

2. 音频转发
   Voice Agent Plugin → Qwen3-Realtime-SDK → 百炼 API

3. STT 结果
   百炼 API → Qwen3-Realtime-SDK → Voice Agent Plugin → 浏览器 (字幕)

4. LLM 处理
   百炼 API 内部处理 (Realtime 模型包含 LLM)

5. TTS 结果
   百炼 API → Qwen3-Realtime-SDK → Voice Agent Plugin → 浏览器 (播放)
```

### 4.3 与 OpenClaw Agent 集成

**问题**: Realtime 模型内置了 LLM，但道友可能希望使用 OpenClaw 的 Agent 系统。

**两种模式**:

| 模式 | 流程 | 适用场景 |
|------|------|----------|
| **直通模式** | 音频 → 百炼 Realtime → 音频 | 快速对话，不需要 OpenClaw 工具 |
| **Agent 模式** | 音频 → STT → OpenClaw Agent → TTS → 音频 | 需要调用工具、访问知识库 |

**推荐**: MVP 阶段使用**直通模式**，后续支持**Agent 模式**。

---

## 5. 项目位置

### 5.1 本地仓库

**位置**: `~/workspaces/voice-agent/`

**结构**:
```
voice-agent/
├── openclaw.plugin.json    # OpenClaw 插件清单
├── package.json            # Node.js 项目
├── src/
│   ├── index.ts            # 插件入口
│   ├── channel/
│   │   └── plugin.ts       # ChannelPlugin 实现
│   ├── websocket/
│   │   └── server.ts       # WebSocket 服务器
│   └── bridge/
│       └── qwen3-bridge.ts # 与 Qwen3-Realtime-SDK 桥接
└── demo/
    └── index.html          # 浏览器演示页面
```

### 5.2 远端仓库

**GitHub**: `https://github.com/openclaw/voice-agent` (待创建)

---

## 6. 开发计划

### Phase 1: 基础框架 (1 天)

| 任务 | 产出 | 验证方法 |
|------|------|----------|
| 创建项目骨架 | `openclaw.plugin.json`, `package.json` | 文件存在 |
| 实现 ChannelPlugin 接口 | `meta`, `capabilities` | OpenClaw 识别插件 |
| WebSocket 服务器 | 监听连接 | wscat 测试连接 |

### Phase 2: 集成 Qwen3-Realtime-SDK (1 天)

| 任务 | 产出 | 验证方法 |
|------|------|----------|
| Python 桥接服务 | 转发 WebSocket 到百炼 | 音频可发送 |
| 音频格式转换 | PCM ↔ Base64 | 格式正确 |
| 回调处理 | 接收 STT/TTS 事件 | 事件可接收 |

### Phase 3: 浏览器客户端 (1 天)

| 任务 | 产出 | 验证方法 |
|------|------|----------|
| HTML 演示页面 | `demo/index.html` | 页面可打开 |
| 音频采集 | MediaRecorder API | 麦克风可用 |
| 音频播放 | Web Audio API | 可播放 |

### Phase 4: OpenClaw 集成 (1 天)

| 任务 | 产出 | 验证方法 |
|------|------|----------|
| Channel 注册 | OpenClaw 识别 channel | `/channels` 可见 |
| 配对机制 | 用户配对 | 可配对用户 |
| 配置集成 | `openclaw.json` 配置 | 配置可加载 |

### Phase 5: 测试与优化 (1 天)

| 任务 | 产出 | 验证方法 |
|------|------|----------|
| 端到端测试 | 完整语音对话 | 说话→回复正常 |
| 延迟优化 | 延迟 < 1s | 测量延迟 |
| 错误处理 | 断线重连 | 重连成功 |

**预计总时长**: 5 天

---

## 7. 技术风险

### 7.1 已知风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 百炼 API 延迟高 | 中 | 高 | 选择国内节点，优化网络 |
| WebSocket 连接不稳定 | 中 | 中 | 实现重连机制 |
| 音频格式不兼容 | 低 | 中 | 严格遵循 PCM 16kHz 规范 |
| 浏览器兼容性 | 低 | 低 | 测试主流浏览器 |

### 7.2 未知风险

- 百炼 API 的速率限制
- 并发连接数限制
- 音频质量要求

---

## 8. 配置设计

### 8.1 OpenClaw 配置

```json5
{
  plugins: {
    entries: {
      "voice-agent": {
        enabled: true,
        config: {
          // WebSocket 服务器
          serve: {
            port: 8765,
            path: "/voice-agent/stream",
          },
          
          // 百炼 API
          bailian: {
            apiKey: "sk-your-api-key-here",
            model: "qwen3-omni-flash-realtime",
            voice: "Chelsie",
          },
          
          // 音频配置
          audio: {
            inputSampleRate: 16000,
            outputSampleRate: 24000,
          },
          
          // 会话配置
          session: {
            maxDurationMs: 300000,
            idleTimeoutMs: 30000,
          },
          
          // 安全配置
          security: {
            pairingRequired: true,
          },
        },
      },
    },
  },
}
```

### 8.2 环境变量

```bash
ALI_BAILIAN_API_KEY=sk-your-api-key-here
```

---

## 9. 决策点

### 9.1 待确认事项

| 事项 | 选项 | 建议 |
|------|------|------|
| **模型选择** | Realtime vs STT+TTS 独立 | Realtime（简单快速） |
| **LLM 集成** | 百炼内置 vs OpenClaw Agent | MVP 用百炼内置，后续支持 Agent |
| **语言选择** | TypeScript vs Python | TypeScript（OpenClaw 插件标准） |
| **音频传输** | Base64 vs Binary | Binary（更高效） |

### 9.2 道友决策

请确认：
1. ✅ 使用 Realtime 模型（qwen3-omni-flash-realtime）
2. ❓ 是否需要 OpenClaw Agent 集成（MVP 阶段可暂不实现）
3. ✅ 项目位置：`~/workspaces/voice-agent/`
4. ❓ 是否创建 GitHub 远端仓库

---

## 10. 下一步

### 10.1 立即行动

1. 道友确认调研结论
2. 创建 GitHub 仓库
3. 初始化本地项目

### 10.2 小步验证计划

**验证 1**: WebSocket 连接
- 目标：浏览器能连接到 WebSocket 服务器
- 时间：30 分钟

**验证 2**: 音频采集
- 目标：浏览器能采集麦克风音频
- 时间：30 分钟

**验证 3**: 百炼连接
- 目标：Python SDK 能连接百炼 API
- 时间：30 分钟

**验证 4**: 端到端
- 目标：说话 → 听到回复
- 时间：1 小时

---

## 11. 参考文档

### 11.1 本地文档

- `~/workspaces/qwen3-realtime-sdk/README.md`
- `~/workspaces/qwen3-realtime-sdk/examples/websocket_server.py`
- `~/.openclaw/workspace-xihe/memory/voice-agent-channel-design.md`

### 11.2 外部文档

- 百炼 Realtime API: https://bailian.console.aliyun.com/
- OpenClaw 插件开发: `/home/ztmdsbt/.npm-global/lib/node_modules/openclaw/docs/plugins/manifest.md`
- OpenClaw Channel 插件: `/home/ztmdsbt/.openclaw/extensions/openclaw-lark/`

---

_调研完成，等待道友确认后进行下一步_