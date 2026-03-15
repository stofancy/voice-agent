# Voice Agent Skill

Voice Agent Channel 的使用指南。

## 功能

- 语音输入 → STT → OpenClaw Agent → TTS → 语音输出
- 支持浏览器端实时交互
- 集成阿里百炼语音服务

## 使用方法

### 1. 配置

在 `openclaw.json` 中配置：

```json5
{
  plugins: {
    entries: {
      "voice-agent": {
        enabled: true,
        config: {
          bailian: {
            apiKey: "sk-xxx",
          },
        },
      },
    },
  },
}
```

### 2. 访问 WebUI

打开浏览器访问：http://localhost:3000

### 3. 语音对话

1. 点击麦克风按钮
2. 说话
3. 松开按钮
4. 等待回复

## 工具

暂无专用工具。

## 配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `serve.port` | WebSocket 端口 | 8765 |
| `serve.path` | WebSocket 路径 | /voice-agent/stream |
| `bailian.apiKey` | 百炼 API Key | 必需 |
| `bailian.sttModel` | STT 模型 | qwen3-asr-flash |
| `bailian.ttsModel` | TTS 模型 | qwen3-tts-instruct-flash |
| `bailian.ttsVoice` | TTS 音色 | Cherry |
