# OpenClaw Voice 项目交接文档

**创建时间**: 2026-03-16 23:59
**最后更新**: 2026-03-17 01:50
**状态**: ✅ 部署完成，流式字幕已合并

---

## 🎉 项目状态

**部署状态**: ✅ 完成
**测试状态**: ✅ 基础功能正常
**流式字幕**: ✅ 代码已合并到 main 分支

---

## 📋 快速部署

```bash
# 1. 进入项目目录
cd ~/workspaces/openclaw-voice

# 2. 启动服务
./start.sh

# 或
docker compose up -d
```

**访问地址**:
- Voice UI: http://localhost:8765/
- Gateway: http://localhost:26523/

---

## 🏗️ 架构说明

```
┌─────────────────────────────────────────────────────────┐
│  ~/workspaces/openclaw-voice/                            │
│                                                         │
│  docker-compose.yml (独立部署)                           │
│  + .env (环境变量)                                       │
│                                                         │
│  ┌────────────────────┐    ┌───────────────────────┐   │
│  │ OpenClaw Gateway   │◄──►│  OpenClaw Voice       │   │
│  │ (Port: 26523)      │    │  (Port: 8765)         │   │
│  │                    │    │                       │   │
│  │ Volume: 独立 Docker │    │  STT: 百炼 qwen3-asr  │   │
│  │ 不挂载 ~/.openclaw │    │  TTS: 百炼 qwen3-tts  │   │
│  └────────────────────┘    │  LLM: → Gateway       │   │
│                            └───────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**核心原则**:
- ❌ 不修改官方 `~/workspaces/openclaw/` 仓库
- ❌ 不挂载主机 `~/.openclaw` 配置
- ✅ 使用独立 Docker volume 存储 Gateway 配置
- ✅ 所有配置通过 `.env` 传递

---

## ✅ 已完成功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 百炼 STT | ✅ | qwen3-asr-flash 语音识别 |
| 百炼 TTS | ✅ | qwen3-tts-flash 语音合成 |
| Gateway 连接 | ✅ | HTTP API (chatCompletions) |
| 流式字幕 | ✅ | 实时显示 AI 回复字幕 |
| Docker 部署 | ✅ | 独立 volume，不触碰主机配置 |

---

## ⏳ 待实现功能

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 百炼实时 STT | 🔴 高 | WebSocket 实时音频流识别 |
| 百炼实时 TTS | 🔴 高 | WebSocket 实时文字流合成 |
| 多音色切换 | 🟢 低 | Cherry/Bella/Sarah/Jack/Allie |
| VAD 优化 | 🟢 低 | 语音活动检测 |
| 连续对话 | 🟢 低 | 类似 Alexa 的连续对话模式 |

---

## 🔧 运维命令

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f openclaw-voice
docker compose logs -f openclaw-gateway

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 重新构建
docker compose build --no-cache openclaw-voice
```

---

## 📝 重要配置

### Gateway 配置（Docker volume）

配置存储在 Docker volume `openclaw-gateway-config` 中：

```bash
# 查看配置
docker run --rm -v openclaw-gateway-config:/home/node/.openclaw \
  ghcr.io/openclaw/openclaw:latest cat /home/node/.openclaw/openclaw.json

# 重新生成配置
docker run --rm --user root \
  -v openclaw-gateway-config:/home/node/.openclaw \
  ghcr.io/openclaw/openclaw:latest \
  sh -c 'cat > /home/node/.openclaw/openclaw.json << EOF
{
  "gateway": {
    "controlUi": {"dangerouslyAllowHostHeaderOriginFallback": true},
    "mode": "local",
    "bind": "lan",
    "port": 18789,
    "http": {"endpoints": {"chatCompletions": {"enabled": true}}}
  },
  "models": {
    "providers": {
      "bailian": {
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "apiKey": "REDACTED-bailian-api-key",
        "api": "openai-completions",
        "models": [{"id": "bailian/qwen3-coder-next", "name": "qwen3-coder-next"}]
      }
    }
  },
  "agents": {"defaults": {"model": "bailian/qwen3-coder-next"}}
}
EOF
chown -R 1000:1000 /home/node/.openclaw'
```

### 环境变量（.env）

```bash
# Gateway 配置
OPENCLAW_GATEWAY_PORT=26523
OPENCLAW_BRIDGE_PORT=26524
OPENCLAW_GATEWAY_TOKEN=REDACTED-openclaw-voice-token

# 百炼 API
ALI_BAILIAN_API_KEY=REDACTED-bailian-api-key

# Voice 配置
OPENCLAW_VOICE_PORT=8765
OPENCLAW_STT_MODEL=qwen3-asr-flash
OPENCLAW_TTS_MODEL=qwen3-tts-flash
OPENCLAW_TTS_VOICE=Cherry
```

---

## 🐛 故障排查

### Gateway 无法启动

```bash
# 查看日志
docker logs openclaw-voice-openclaw-gateway-1

# 检查配置
docker run --rm -v openclaw-gateway-config:/home/node/.openclaw \
  ghcr.io/openclaw/openclaw:latest cat /home/node/.openclaw/openclaw.json

# 重新生成配置（见上方）
```

### Voice 无法连接 Gateway

```bash
# 检查 Gateway 是否运行
docker ps | grep openclaw-gateway

# 测试 Gateway 连通性
curl http://localhost:26523/healthz

# 查看 Voice 日志
docker logs openclaw-voice-openclaw-voice-1
```

### STT/TTS 失败

```bash
# 检查 API Key
cat .env | grep ALI_BAILIAN_API_KEY

# 测试百炼 API
curl -X POST 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions' \
  -H "Authorization: Bearer $ALI_BAILIAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-asr-flash","messages":[{"role":"user","content":[{"type":"input_audio","input_audio":{"data":"data:audio/wav;base64,..."}}]}]}'
```

---

## 📚 相关文档

| 文档 | 位置 |
|------|------|
| 部署日志 | `memory/2026-03-17.md` |
| 待办事项 | `TODOS.md` |
| 百炼 STT API | `~/workspaces/voice-agent/语音识别 API.md` |
| 百炼 TTS API | `~/workspaces/voice-agent/语音合成 API.md` |

---

*最后更新：2026-03-17 01:50*
*维护者：九章*
