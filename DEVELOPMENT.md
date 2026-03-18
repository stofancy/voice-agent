# OpenClaw Voice - 开发与部署指南

## 📐 架构设计

### 生产环境（三容器分离）

| 容器 | 端口 | 说明 |
|------|------|------|
| `openclaw-gateway` | 26523 | Gateway 服务 |
| `openclaw-voice-backend` | 8765 | FastAPI 后端 |
| `openclaw-voice-frontend` | 8764 | Nginx 静态文件 |

```
┌─────────────────────────────────────────┐
│         Docker Compose                  │
│  ┌───────────────────────────────────┐  │
│  │  openclaw-gateway (18789 → 26523) │  │
│  └───────────────────────────────────┘  │
│                    ↑                     │
│  ┌───────────────────────────────────┐  │
│  │  openclaw-voice-backend (8765)    │  │
│  │  - FastAPI + STT/TTS              │  │
│  └───────────────────────────────────┘  │
│                    ↑                     │
│  ┌───────────────────────────────────┐  │
│  │  openclaw-voice-frontend (8764)   │  │
│  │  - Nginx + React                  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 开发环境（本地 + Docker）

| 服务 | 端口 | 说明 |
|------|------|------|
| Gateway (Docker) | 26523 | 仅 Gateway 容器 |
| 前端本地 | 5173 | Vite HMR |
| 后端本地 | 8766 | Uvicorn --reload |

```
┌─────────────────────────────────────────┐
│         Docker (Gateway Only)           │
│  ┌───────────────────────────────────┐  │
│  │  openclaw-gateway (18789 → 26523) │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                    ↑ WebSocket/API
┌─────────────────────────────────────────┐
│         本地开发环境                     │
│  ┌───────────────────────────────────┐  │
│  │  Vite Dev Server (5173)           │  │
│  │  - 前端 HMR                        │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Uvicorn --reload (8766)          │  │
│  │  - 后端热重载                       │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## 🚀 生产部署

### 一键部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 Bailian API Key

# 2. 部署
./scripts/deploy.sh

# 3. 访问
# 前端：http://localhost:8764/
# 后端 API: http://localhost:8765/
```

### 单独控制

```bash
# 只重启前端
docker compose restart openclaw-voice-frontend

# 只重启后端
docker compose restart openclaw-voice-backend

# 查看后端日志
docker compose logs -f openclaw-voice-backend

# 查看前端日志
docker compose logs -f openclaw-voice-frontend
```

---

## 💻 本地开发

### 启动步骤

```bash
# 1. 启动 Gateway（Docker）
docker compose -f docker-compose.dev.yml up -d

# 2. 启动后端（本地）
cd ~/workspaces/voice-agent
source .env.development
python -m uvicorn src/server.main:app --reload --port 8766

# 3. 启动前端（本地）
cd src/client/v2-react
npm run dev
```

### 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端开发 | http://localhost:5173/ | Vite HMR |
| 后端开发 | http://localhost:8766/ | Uvicorn |
| Gateway | http://localhost:26523/ | Docker |

---

## 🔧 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ALI_BAILIAN_API_KEY` | 百炼 API 密钥 | - |
| `OPENCLAW_GATEWAY_TOKEN` | Gateway 认证令牌 | `openclaw-your-gateway-token-here` |
| `OPENCLAW_BACKEND_PORT` | 后端端口 | `8765` |
| `OPENCLAW_FRONTEND_PORT` | 前端端口 | `8764` |
| `OPENCLAW_STT_MODEL` | STT 模型 | `qwen3-asr-flash` |
| `OPENCLAW_TTS_MODEL` | TTS 模型 | `qwen3-tts-flash` |
| `OPENCLAW_TTS_VOICE` | TTS 音色 | `Cherry` |

### Gateway 连接

**生产环境**（Docker 网络）：
```bash
OPENCLAW_GATEWAY_URL=http://openclaw-gateway:18789
```

**开发环境**（本地连接 Docker）：
```bash
OPENCLAW_GATEWAY_URL=http://localhost:26523
```

---

## 📋 常用命令

### 生产环境
```bash
# 部署
./scripts/deploy.sh

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f

# 停止
docker compose down

# 重新构建
docker compose build --no-cache
```

### 开发环境
```bash
# 启动 Gateway
docker compose -f docker-compose.dev.yml up -d

# 停止 Gateway
docker compose -f docker-compose.dev.yml down

# 查看 Gateway 日志
docker compose logs -f openclaw-gateway
```

---

## 🔍 故障排查

### Gateway 连接失败

```bash
# 检查 Gateway 状态
docker compose ps

# 测试 Gateway 健康
curl http://localhost:26523/health

# 查看 Gateway 日志
docker compose logs openclaw-gateway
```

### 后端 404

```bash
# 检查后端状态
curl http://localhost:8765/

# 查看后端日志
docker compose logs openclaw-voice-backend
```

### 前端 404

```bash
# 检查前端状态
curl http://localhost:8764/

# 查看前端日志
docker compose logs openclaw-voice-frontend

# 重新构建前端
docker compose build openclaw-voice-frontend
docker compose restart openclaw-voice-frontend
```

---

## 📊 端口分配

| 服务 | 容器内端口 | 主机端口 | 说明 |
|------|-----------|---------|------|
| Gateway | 18789 | 26523 | Gateway API |
| Gateway | 18790 | 26524 | Gateway 控制 |
| Backend | 8765 | 8765 | FastAPI |
| Frontend | 80 | 8764 | Nginx |
| Dev Frontend | 5173 | 5173 | Vite (本地) |
| Dev Backend | 8766 | 8766 | Uvicorn (本地) |

---

## 🎯 架构优势

### 前后端分离

| 优势 | 说明 |
|------|------|
| ✅ 独立扩展 | 前端/后端可独立扩容 |
| ✅ 独立部署 | 前端更新无需重启后端 |
| ✅ 技术栈独立 | 前端用 Nginx，后端用 Python |
| ✅ 缓存优化 | Nginx 可配置静态资源缓存 |

### 开发/生产一致

| 特性 | 说明 |
|------|------|
| ✅ 相同 Gateway | 开发/生产使用同一 Gateway |
| ✅ 相同配置 | 环境变量管理一致 |
| ✅ 快速切换 | `docker compose` vs `npm run dev` |

---

*最后更新：2026-03-18*
