# Voice Agent 快速启动指南

## 前置条件

1. **Node.js >= 18**
```bash
node --version  # 应 >= v18.0.0
```

2. **阿里百炼 API Key**
   - 获取地址：https://bailian.console.aliyun.com/
   - 需要开通：STT（语音识别）+ TTS（语音合成）

3. **OpenClaw Gateway**
   - 确保 Gateway 正在运行
   - 获取 Gateway Token

---

## 快速启动

### 1. 安装依赖

```bash
cd ~/workspaces/voice-agent
npm install
```

### 2. 设置环境变量

```bash
export ALI_BAILIAN_API_KEY="sk-your-api-key-here"
export OPENCLAW_GATEWAY_URL="http://127.0.0.1:18789"
export OPENCLAW_GATEWAY_TOKEN="your-gateway-token"
```

### 3. 构建后端

```bash
cd packages/server
npm run build
```

### 4. 安装插件到 OpenClaw

```bash
# 方式 A：使用 OpenClaw CLI
cd ~/workspaces/voice-agent
openclaw plugins install ./packages/server/dist

# 方式 B：手动配置
# 编辑 ~/.openclaw/openclaw.json
{
  "plugins": {
    "entries": {
      "voice-agent": {
        "enabled": true,
        "config": {
          "bailian": {
            "apiKey": "sk-your-api-key"
          },
          "gateway": {
            "url": "http://127.0.0.1:18789",
            "token": "your-gateway-token"
          }
        }
      }
    }
  }
}
```

### 5. 重启 OpenClaw Gateway

```bash
openclaw gateway restart
```

### 6. 启动 WebUI 开发服务器

```bash
cd packages/webui
npm run dev
```

访问：http://localhost:5173

---

## 测试流程

1. **打开浏览器** 访问 WebUI
2. **点击麦克风按钮** 开始录音
3. **说话**（例如："你好，帮我订个酒店"）
4. **松开按钮** 停止录音
5. **等待回复** - 应该听到 TTS 播放的回复

---

## 故障排查

### WebSocket 连接失败

```bash
# 检查服务器是否运行
curl http://localhost:8765

# 查看服务器日志
tail -f ~/.openclaw/logs/gateway.log
```

### STT/TTS API 错误

```bash
# 验证 API Key
curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer $ALI_BAILIAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-turbo","messages":[{"role":"user","content":"test"}]}'
```

### Agent 无响应

```bash
# 检查 Gateway 状态
openclaw status

# 检查 Agent 配置
openclaw agents list
```

---

## 配置选项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `serve.port` | 8765 | WebSocket 服务器端口 |
| `serve.path` | `/voice-agent/stream` | WebSocket 路径 |
| `bailian.sttModel` | `qwen3-asr-flash` | STT 模型 |
| `bailian.ttsModel` | `qwen3-tts-instruct-flash` | TTS 模型 |
| `bailian.ttsVoice` | `Cherry` | TTS 声音 |
| `session.maxDurationMs` | 300000 | 会话最大时长（5 分钟） |
| `session.idleTimeoutMs` | 30000 | 空闲超时（30 秒） |

---

## 架构说明

```
┌─────────────┐     WebSocket      ┌─────────────┐
│   WebUI     │ ◄────────────────► │   Server    │
│  (React)    │   (音频流/Base64)   │  (Node.js)  │
└─────────────┘                    └──────┬──────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     ▼                     ▼
              ┌──────────┐         ┌──────────┐         ┌──────────┐
              │   STT    │         │  Agent   │         │   TTS    │
              │ (阿里云)  │         │(OpenClaw)│         │ (阿里云)  │
              └──────────┘         └──────────┘         └──────────┘
```

---

**最后更新**: 2026-03-15
