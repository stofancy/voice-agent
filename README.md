# Voice Agent - OpenClaw Channel Plugin

浏览器端语音交互插件，集成阿里百炼 STT/TTS 和 OpenClaw Agent。

## ✨ 特性

- 🎤 **实时语音输入** - 浏览器麦克风采集，WebSocket 传输
- 🗣️ **语音识别** - 阿里百炼 `qwen3-asr-flash`
- 💬 **OpenClaw Agent** - 智能回复和工具调用
- 🔊 **语音合成** - 阿里百炼 `qwen3-tts-instruct-flash`
- 📱 **响应式设计** - Mobile First，支持各种设备
- 🎨 **流畅动画** - Framer Motion 驱动

## 📦 安装

### 1. 安装依赖

```bash
cd ~/workspaces/voice-agent
npm install
```

### 2. 配置 API Key

```bash
# 方法 1: 环境变量
export ALI_BAILIAN_API_KEY=sk-xxx

# 方法 2: OpenClaw 配置
# 在 openclaw.json 中配置 plugins.entries.voice-agent.config.bailian.apiKey
```

### 3. 安装到 OpenClaw

```bash
# 构建
npm run build

# 安装插件
openclaw plugins install ./packages/server/dist
```

### 4. 配置 OpenClaw

```json5
{
  plugins: {
    entries: {
      "voice-agent": {
        enabled: true,
        config: {
          serve: {
            port: 8765,
            path: "/voice-agent/stream",
          },
          bailian: {
            apiKey: "sk-xxx",
            sttModel: "qwen3-asr-flash",
            ttsModel: "qwen3-tts-instruct-flash",
            ttsVoice: "Cherry",
          },
        },
      },
    },
  },
}
```

### 5. 重启 Gateway

```bash
openclaw gateway restart
```

## 🚀 使用

### 启动 WebUI

```bash
cd packages/webui
npm run dev
```

访问 http://localhost:3000

### 连接流程

1. 打开浏览器页面
2. 等待 WebSocket 自动连接
3. 点击麦克风按钮开始说话
4. 说完后松开，等待回复

## 📁 项目结构

```
voice-agent/
├── packages/
│   ├── server/          # OpenClaw 插件（后端）
│   │   ├── src/
│   │   │   ├── channel/     # Channel 实现
│   │   │   ├── websocket/   # WebSocket 服务器
│   │   │   ├── stt/         # STT 客户端
│   │   │   ├── tts/         # TTS 客户端
│   │   │   └── session/     # 会话管理
│   │   └── package.json
│   └── webui/           # 浏览器前端
│       ├── src/
│       │   ├── components/
│       │   ├── store/
│       │   └── utils/
│       └── package.json
├── docs/                # 文档
├── openclaw.plugin.json # 插件清单
└── package.json
```

## 🔧 开发

### 后端开发

```bash
cd packages/server
npm run dev    # TypeScript 监视模式
npm run build  # 构建
```

### 前端开发

```bash
cd packages/webui
npm run dev    # Vite 开发服务器
npm run build  # 构建生产版本
```

## 📝 API

### WebSocket 协议

**客户端 → 服务端**:
```typescript
{ type: 'audio', data: { payload: string, ... } }
{ type: 'control', action: 'start' | 'stop' }
```

**服务端 → 客户端**:
```typescript
{ type: 'transcript', data: { text: string, isFinal: boolean } }
{ type: 'audio_output', data: { payload: string, isChunk: boolean } }
{ type: 'status', state: 'listening' | 'processing' | 'speaking' }
```

## ⚠️ 注意事项

1. **音频格式**: 输入音频必须是 PCM 16kHz 16bit 单声道
2. **API Key**: 需要从阿里云百炼控制台获取
3. **浏览器权限**: 需要麦克风权限
4. **网络**: WebSocket 需要稳定连接

## 📄 许可证

MIT License
