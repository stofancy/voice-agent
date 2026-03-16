# OpenClaw Voice - Bailian Edition

**Docker-based voice interface for OpenClaw, powered by Alibaba Bailian STT/TTS.**

这是基于 Purple-Horizons/openclaw-voice 项目修改的版本，集成了**阿里百炼语音 API**（STT + TTS），可在 Docker 隔离环境中测试 voice capability。

---

## ✨ 特性

- 🎤 **百炼 STT** - `qwen3-asr-flash` 语音识别（中文优化）
- 🔊 **百炼 TTS** - `qwen3-tts-flash` 语音合成（Cherry 等音色）
- 🦞 **OpenClaw 集成** - 可连接主公的 OpenClaw Gateway
- 🐳 **Docker 隔离** - 完全隔离，不影响生产环境
- 🌐 **浏览器界面** - WebSocket 实时语音交互

---

## 🚀 快速启动

### 1. 启动 Docker 容器

```bash
cd ~/workspaces/openclaw-voice
./scripts/start-bailian.sh
```

或手动启动：

```bash
docker-compose -f docker-compose.bailian.yml up --build -d
```

### 2. 访问 Web 界面

打开浏览器访问：**http://localhost:8765**

### 3. 测试语音

1. 点击麦克风按钮
2. 说话（中文）
3. 松开按钮，等待回复
4. 应该听到 TTS 播放的回复

---

## 📋 配置说明

### 环境变量（`.env`）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ALI_BAILIAN_API_KEY` | `YOUR_BAILIAN_API_KEY` | 百炼 API Key |
| `OPENCLAW_GATEWAY_URL` | `http://host.docker.internal:7777` | OpenClaw Gateway URL |
| `OPENCLAW_GATEWAY_TOKEN` | `e10b3c7ca70ebef49b27040a1cd6219f59e7a445d4795ee2` | Gateway Token |
| `OPENCLAW_STT_MODEL` | `qwen3-asr-flash` | STT 模型 |
| `OPENCLAW_TTS_MODEL` | `qwen3-tts-flash` | TTS 模型 |
| `OPENCLAW_TTS_VOICE` | `Cherry` | TTS 音色 |

### 可用配置

**STT 模型**：
- `qwen3-asr-flash` - 快速，准确，≤5 分钟
- `qwen3-asr-flash-filetrans` - 长音频（≤12 小时，异步）

**TTS 模型**：
- `qwen3-tts-flash` - 快速，经济
- `qwen3-tts-instruct-flash` - 支持指令控制（语调、语速、情感）

**TTS 音色**：
- `Cherry` - 甜美女性（默认）
- `Bella` - 温柔女性
- `Sarah` - 成熟女性
- `Jack` - 沉稳男性
- `Allie` - 活泼女性

---

## 🔧 故障排查

### 查看日志

```bash
docker-compose -f docker-compose.bailian.yml logs -f
```

### 测试百炼 API

```bash
# 测试 STT
curl -X POST 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions' \
  -H "Authorization: Bearer $ALI_BAILIAN_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen3-asr-flash",
    "messages": [{
      "role": "user",
      "content": [{
        "type": "input_audio",
        "input_audio": {
          "data": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"
        }
      }]
    }]
  }'

# 测试 TTS
curl -X POST 'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation' \
  -H "Authorization: Bearer $ALI_BAILIAN_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen3-tts-flash",
    "input": {
      "text": "你好，这是测试语音",
      "voice": "Cherry"
    }
  }'
```

### 常见问题

**Q: WebSocket 连接失败**
```bash
# 检查容器是否运行
docker-compose -f docker-compose.bailian.yml ps

# 检查端口是否占用
lsof -i :8765
```

**Q: STT/TTS API 错误**
- 验证 API Key 是否正确
- 检查网络连接
- 查看容器日志

**Q: 无法连接 OpenClaw Gateway**
- 确认 Gateway 正在运行：`openclaw status`
- Docker 使用 `host.docker.internal` 访问主机
- 检查防火墙设置

---

## 📁 项目结构

```
openclaw-voice/
├── src/server/
│   ├── main.py              # 主服务（已修改为百炼集成）
│   ├── bailian_stt.py       # 百炼 STT 模块（新增）
│   ├── bailian_tts.py       # 百炼 TTS 模块（新增）
│   ├── backend.py           # AI 后端（已修改支持 Gateway）
│   ├── ...
├── scripts/
│   ├── start-bailian.sh     # 启动脚本
├── docker-compose.bailian.yml  # Docker 配置
├── Dockerfile.bailian          # Docker 镜像
├── .env.bailian                # 配置模板
└── README.bailian.md           # 本文档
```

---

## 🔒 安全说明

- ✅ **完全隔离** - Docker 容器运行，不影响生产环境
- ✅ **只读连接** - 仅读取 Gateway，不修改配置
- ✅ **API Key 保护** - 敏感信息在 `.env` 中，不提交 Git

---

## 📝 技术架构

```
┌─────────────┐    WebSocket    ┌──────────────────────────────────────┐
│   Browser   │◄───────────────►│     OpenClaw Voice (Docker)          │
│  (mic/spk)  │                 │                                      │
└─────────────┘                 │  ┌────────────┐  ┌────────────────┐ │
                                │  │ Bailian STT│→│ OpenClaw Agent │ │
                                │  │ (qwen-asr) │  │   (Gateway)    │ │
                                │  └────────────┘  └───────┬────────┘ │
                                │                          │           │
                                │                    ┌─────▼─────┐    │
                                │                    │Bailian TTS│    │
                                │                    │(qwen-tts) │    │
                                │                    └───────────┘    │
                                └──────────────────────────────────────┘
```

---

## 📚 参考文档

- [百炼语音识别 API](~/workspaces/voice-agent/语音识别 API.md)
- [百炼语音合成 API](~/workspaces/voice-agent/语音合成 API.md)
- [OpenClaw Voice 原项目](https://github.com/Purple-Horizons/openclaw-voice)

---

**Made with 🦞 for 问天君**

最后更新：2026-03-16
