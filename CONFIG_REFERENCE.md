# Voice Agent 配置参考

## 🚀 快速开始

### 查看帮助（脚本自说明）
```bash
./start.sh              # 显示简要帮助
./start.sh help         # 显示详细帮助
./start.sh --help       # 显示详细帮助
./start.sh -h           # 显示简要帮助
./start.sh --version    # 显示版本信息
```

### 本地开发模式（推荐）
```bash
# 1. 启动 Gateway (Docker)
./start.sh gateway start

# 2. 启动 Voice Agent (本地)
./start.sh local start

# 访问
# - Voice: http://localhost:8766/
# - Gateway: http://localhost:18789/
```

### Docker 完整部署
```bash
# 启动所有服务
./start.sh docker up

# 访问
# - Voice: http://localhost:8765/
# - Gateway: http://localhost:18789/
```

| 服务 | 运行方式 | 端口 | 说明 |
|------|---------|------|------|
| **Gateway** | Docker | 18789 | OpenClaw Gateway HTTP API |
| **Voice (Docker)** | Docker | 8765 | Docker 模式下的 Voice Agent |
| **Voice (Local)** | 本地 Python | 8766 | 本地开发模式下的 Voice Agent |

## 🔑 认证配置

### Gateway Token
```
Token: 6c10193f197ddd41233fdf7c57b4d28c3b0cee7c3d11d048
位置：~/voice-agent-data/gateway-config/openclaw.json
```

### .env 配置
```bash
# LLM - 通过 Gateway 调用
OPENCLAW_LLM_PROVIDER=openclaw_gateway
OPENCLAW_LLM_API_KEY=6c10193f197ddd41233fdf7c57b4d28c3b0cee7c3d11d048
OPENCLAW_LLM_MODEL=main
OPENCLAW_LLM_BASE_URL=http://localhost:18789/v1

# STT - 直接调用百炼
OPENCLAW_STT_PROVIDER=bailian
OPENCLAW_STT_API_KEY=sk-REDACTED-bailian-api-key
OPENCLAW_STT_MODEL=qwen3-asr-flash

# TTS - 直接调用百炼实时 API
OPENCLAW_TTS_PROVIDER=bailian_realtime
OPENCLAW_TTS_API_KEY=sk-REDACTED-bailian-api-key
OPENCLAW_TTS_MODEL=qwen3-tts-flash-realtime
OPENCLAW_TTS_VOICE=Maia

# Voice Agent 端口（本地模式）
OPENCLAW_PORT=8766
```

## 🚀 启动方式

### 本地开发模式（推荐）
```bash
# 1. 启动 Gateway (Docker)
./start.sh gateway start

# 2. 启动 Voice Agent (本地)
./start.sh local start

# 访问
# - Voice: http://localhost:8766/
# - Gateway: http://localhost:18789/
```

### Docker 完整部署
```bash
# 启动所有服务
./start.sh docker up

# 访问
# - Voice: http://localhost:8765/
# - Gateway: http://localhost:18789/
```

## 🔧 连接验证

### 检查 Gateway
```bash
curl http://localhost:18789/
# 应返回 HTML 页面
```

### 检查 Voice Agent
```bash
# 本地模式
curl http://localhost:8766/

# Docker 模式
curl http://localhost:8765/
```

### 测试 LLM 连接
```bash
# 通过 Gateway API 测试 LLM
curl http://localhost:18789/v1/chat/completions \
  -H "Authorization: Bearer 6c10193f197ddd41233fdf7c57b4d28c3b0cee7c3d11d048" \
  -H "Content-Type: application/json" \
  -d '{"model":"main","messages":[{"role":"user","content":"hello"}]}'
```

## 📝 日志位置

| 日志 | 位置 |
|------|------|
| **Voice (Local)** | `~/workspaces/voice-agent/.voice.log` |
| **Gateway (Docker)** | `docker compose logs openclaw-gateway` |
| **Voice (Docker)** | `docker compose logs openclaw-voice` |

## ⚠️ 常见问题

### 端口冲突
```bash
# 检查端口占用
lsof -i :8765
lsof -i :8766
lsof -i :18789

# 停止冲突进程
pkill -f "uvicorn src.server.main"
```

### Gateway 连接失败
1. 检查 Gateway 是否运行：`./start.sh gateway status`
2. 检查 Token 是否正确：对比 `.env` 和 `gateway-config/openclaw.json`
3. 检查 Base URL：应为 `http://localhost:18789/v1`

### Voice Agent 无法启动
1. 检查端口是否被占用
2. 查看日志：`tail .voice.log`
3. 检查虚拟环境：`source .venv/bin/activate`
