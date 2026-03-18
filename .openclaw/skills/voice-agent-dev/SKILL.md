# Voice Agent 开发技能

**适用场景**：OpenClaw Voice 项目的开发、调试、部署

**位置**：`~/workspaces/voice-agent/`

---

## 🚀 快速启动

### 本地开发模式（推荐）

```bash
cd ~/workspaces/voice-agent

# 1. 启动后端（端口 8766）
source .venv/bin/activate
python -m uvicorn src.server.main:app --host 0.0.0.0 --port 8766 --reload

# 2. 启动前端（端口 5173，新终端）
cd src/client/v2-react
npm run dev
```

**访问地址**：
- 前端：http://localhost:5173/v2/
- 后端 API：http://localhost:8766/
- 健康检查：http://localhost:8766/health

### 生产部署模式

```bash
cd ~/workspaces/voice-agent
./scripts/deploy.sh
```

**访问地址**：
- 前端：http://localhost:8764/
- 后端 API：http://localhost:8765/
- Gateway：http://localhost:26523/

---

## 📋 核心脚本

| 脚本 | 用途 | 命令 |
|------|------|------|
| `scripts/dev-all.sh` | 启动所有本地开发服务 | `./scripts/dev-all.sh` |
| `scripts/dev-backend.sh` | 仅启动后端 | `./scripts/dev-backend.sh` |
| `scripts/dev-frontend.sh` | 仅启动前端 | `./scripts/dev-frontend.sh` |
| `scripts/deploy.sh` | 生产部署 | `./scripts/deploy.sh` |
| `scripts/stop-all.sh` | 停止所有服务 | `./scripts/stop-all.sh` |

---

## 🔧 配置文件

### `.env.local`（本地开发）

```bash
# Bailian API Key
OPENCLAW_BAILIAN_API_KEY=sk-your-key-here

# 后端配置
OPENCLAW_HOST=0.0.0.0
OPENCLAW_PORT=8766
OPENCLAW_STT_MODEL=qwen3-asr-flash
OPENCLAW_TTS_MODEL=qwen3-tts-flash
OPENCLAW_TTS_VOICE=Cherry

# Gateway（Docker 容器）
OPENCLAW_GATEWAY_URL=http://localhost:26523
OPENCLAW_GATEWAY_TOKEN=openclaw-your-gateway-token-here
```

### `docker-compose.yml`（生产环境）

- Gateway 端口：26523
- 后端端口：8765
- 前端端口：8764

---

## 🐛 故障排查

### 后端启动失败

```bash
# 检查端口占用
lsof -i :8766

# 检查 Python 依赖
source .venv/bin/activate
pip install -r requirements.txt

# 查看日志
docker compose logs openclaw-gateway
```

### 前端无法连接后端

1. 确认后端运行：`curl http://localhost:8766/health`
2. 检查前端 API URL 配置（`vite.config.ts` base: '/v2/'）
3. 检查 CORS 配置

### Gateway 连接失败

```bash
# 检查容器状态
docker compose ps

# 重启 Gateway
docker compose restart openclaw-gateway

# 查看日志
docker compose logs -f openclaw-gateway
```

---

## 📖 相关文档

- `docs/DEVELOPMENT.md` - 详细开发指南
- `docs/AI_DEV_GUIDE.md` - AI 助手通用指南
- `README.md` - 项目概述

---

*最后更新：2026-03-18*
