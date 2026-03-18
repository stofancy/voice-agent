# 本地开发指南

## 架构说明

本地开发环境使用**前后端分离**模式，与 Docker 生产环境保持一致：

```
┌─────────────────────────────────────────────────────────┐
│                  本地开发环境                            │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐            │
│  │  Vite Dev Server│    │   Uvicorn       │            │
│  │  (前端)         │    │   (后端)        │            │
│  │  :5173          │    │   :8766         │            │
│  │                 │───→│                 │            │
│  │  HMR 热更新      │    │   STT/TTS/LLM   │            │
│  └─────────────────┘    └──────┬──────────┘            │
│                                │                        │
│                                ↓                        │
│                      ┌─────────────────┐               │
│                      │  Docker Gateway │               │
│                      │  :26523         │               │
│                      └─────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

## 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| **前端 (Vite)** | 5173 | 开发服务器，支持 HMR |
| **后端 (Uvicorn)** | 8766 | FastAPI 后端（Docker 用 8765） |
| **Gateway (Docker)** | 26523 | OpenClaw Gateway 容器 |

## 快速启动

### 0. 前置条件

```bash
# 确保 Gateway 容器运行
cd ~/workspaces/voice-agent
docker compose up -d openclaw-gateway

# 确保 Python 虚拟环境已创建
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 1. 启动后端

```bash
cd ~/workspaces/voice-agent
source .venv/bin/activate
python -m uvicorn src.server.main:app --host 0.0.0.0 --port 8766 --reload
```

**访问**：
- 健康检查：http://localhost:8766/health
- API 文档：http://localhost:8766/docs

### 2. 启动前端（新终端）

```bash
cd ~/workspaces/voice-agent/src/client/v2-react
npm run dev
```

**访问**：http://localhost:5173/v2/

### 3. 一键启动脚本

```bash
# 启动所有服务
./scripts/dev.sh

# 或手动启动
./scripts/dev-backend.sh &
./scripts/dev-frontend.sh &
```

## 配置文件

### `.env.local`（后端）

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

### `vite.config.ts`（前端）

```typescript
export default defineConfig({
  plugins: [react()],
  base: '/v2/',  // ← 重要：API 路由前缀
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

## 开发工作流

### 前端开发

- ✅ **HMR 热更新**：修改代码后自动刷新
- ✅ **TypeScript**：类型检查
- ✅ **ESLint**：代码规范

```bash
# 类型检查
npm run type-check

# 代码检查
npm run lint

# 构建生产版本
npm run build
```

### 后端开发

- ✅ **自动重载**：修改代码后自动重启
- ✅ **API 文档**：http://localhost:8766/docs
- ✅ **健康检查**：http://localhost:8766/health

```bash
# 测试 API
curl http://localhost:8766/health

# 查看日志
# uvicorn 会自动输出到终端
```

### 调试 Gateway

```bash
# 查看 Gateway 日志
docker compose logs -f openclaw-gateway

# 重启 Gateway
docker compose restart openclaw-gateway

# 进入容器
docker exec -it openclaw-voice-openclaw-gateway-1 sh
```

## 与 Docker 生产环境的区别

| 方面 | 本地开发 | Docker 生产 |
|------|----------|-------------|
| 后端端口 | 8766 | 8765 |
| 前端端口 | 5173 (Vite) | 8764 (Nginx) |
| 代码更新 | 实时 HMR/重载 | 需重新构建镜像 |
| 调试 | 支持断点/日志 | 查看容器日志 |
| 依赖 | 本地 .venv/node_modules | Docker 镜像内 |

## 部署到生产

```bash
# 停止本地开发服务
pkill -f "uvicorn src.server.main"
pkill -f "vite"

# 构建并部署
./scripts/deploy.sh
```

## 常见问题

### Q: 后端启动失败，提示端口被占用
A: 检查是否有 Docker 容器占用 8766 端口，或修改 `.env.local` 中的 `OPENCLAW_PORT`

### Q: 前端无法连接后端
A: 检查前端代码中的 API URL 是否指向 `localhost:8766`

### Q: Gateway 连接失败
A: 确保 Docker 容器运行：`docker compose ps openclaw-gateway`

---

*最后更新：2026-03-18*
