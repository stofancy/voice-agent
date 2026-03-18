# AI 助手开发指南 - OpenClaw Voice

**适用对象**：Copilot、Claude Code、OpenCode、Cursor 等所有 AI 编程助手

**项目位置**：`~/workspaces/voice-agent/`

---

## 🎯 快速开始

### 首次设置

```bash
cd ~/workspaces/voice-agent

# 1. 创建 Python 虚拟环境
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. 安装前端依赖
cd src/client/v2-react
npm install

# 3. 配置环境变量
cd ~/workspaces/voice-agent
cp .env.example .env.local
# 编辑 .env.local 填入 Bailian API Key
```

### 启动开发环境

**方式 A：一键启动（推荐）**
```bash
./scripts/dev-all.sh
```

**方式 B：分步启动**
```bash
# 终端 1：后端
./scripts/dev-backend.sh

# 终端 2：前端
./scripts/dev-frontend.sh
```

### 验证服务

```bash
# 后端健康检查
curl http://localhost:8766/health

# 前端页面
curl http://localhost:5173/v2/
```

---

## 📁 项目结构

```
voice-agent/
├── src/
│   ├── server/              # Python FastAPI 后端
│   │   ├── main.py          # 应用入口
│   │   ├── bailian_stt.py   # 语音识别
│   │   ├── bailian_tts.py   # 语音合成
│   │   ├── backend.py       # LLM 后端
│   │   └── vad.py           # 语音活动检测
│   └── client/v2-react/     # React 前端
│       ├── src/
│       │   ├── App.tsx
│       │   ├── components/
│       │   └── hooks/
│       └── package.json
├── scripts/                 # 可执行脚本
│   ├── dev-all.sh          # 启动所有服务
│   ├── dev-backend.sh      # 启动后端
│   ├── dev-frontend.sh     # 启动前端
│   ├── deploy.sh           # 生产部署
│   └── stop-all.sh         # 停止所有服务
├── docker-compose.yml       # 生产环境配置
├── .env.local               # 本地开发配置
├── requirements.txt         # Python 依赖
└── docs/                    # 文档
    ├── AI_DEV_GUIDE.md     # 本文件
    └── DEVELOPMENT.md      # 详细开发指南
```

---

## 🔧 核心配置

### 端口分配

| 服务 | 开发环境 | 生产环境 | 说明 |
|------|----------|----------|------|
| 后端 | 8766 | 8765 | FastAPI |
| 前端 | 5173 | 8764 | Vite / Nginx |
| Gateway | 26523 | 26523 | Docker 容器 |

### 环境变量 (`.env.local`)

```bash
# Bailian API Key（必需）
OPENCLAW_BAILIAN_API_KEY=sk-xxx

# 后端配置
OPENCLAW_PORT=8766
OPENCLAW_STT_MODEL=qwen3-asr-flash
OPENCLAW_TTS_MODEL=qwen3-tts-flash
OPENCLAW_TTS_VOICE=Cherry

# Gateway 配置
OPENCLAW_GATEWAY_URL=http://localhost:26523
OPENCLAW_GATEWAY_TOKEN=openclaw-your-gateway-token-here
```

---

## 🤖 AI 助手工作流

### 代码修改后

1. **Python 后端**：Uvicorn 自动重载（`--reload` 参数）
2. **React 前端**：Vite HMR 自动刷新
3. **验证**：访问 http://localhost:5173/v2/ 测试功能

### 添加依赖

```bash
# Python
source .venv/bin/activate
pip install <package>
pip freeze >> requirements.txt

# Node.js
cd src/client/v2-react
npm install <package>
```

### 调试技巧

```bash
# 查看后端日志
# uvicorn 直接输出到终端

# 查看 Gateway 日志
docker compose logs -f openclaw-gateway

# 检查端口占用
lsof -i :8766
lsof -i :5173

# 测试 API
curl http://localhost:8766/health
curl http://localhost:8766/docs  # Swagger UI
```

---

## 🚀 生产部署

```bash
cd ~/workspaces/voice-agent
./scripts/deploy.sh
```

**部署后访问**：
- 前端：http://localhost:8764/
- 后端：http://localhost:8765/health

---

## 🐛 常见问题

| 问题 | 解决方案 |
|------|----------|
| 端口 8766 被占用 | `lsof -i :8766` 查找并停止进程 |
| Gateway 未运行 | `docker compose up -d openclaw-gateway` |
| 前端构建失败 | `cd src/client/v2-react && npm install` |
| STT/TTS 错误 | 检查 `.env.local` 中 API Key |
| WebSocket 连接失败 | 确认后端运行且端口正确 |

---

## 📖 相关文档

- **本文件** (`docs/AI_DEV_GUIDE.md`) - AI 助手快速指南
- **`docs/DEVELOPMENT.md`** - 详细开发文档
- **`README.md`** - 项目概述
- **`.github/copilot-instructions.md`** - GitHub Copilot 专用
- **`.claude/instructions.md`** - Claude Code 专用
- **`.openclaw/skills/voice-agent-dev/SKILL.md`** - OpenClaw Skill

---

## ✅ 检查清单

开发新功能时：

- [ ] 后端代码修改后，验证 `curl http://localhost:8766/health`
- [ ] 前端代码修改后，浏览器自动刷新
- [ ] WebSocket 连接正常（浏览器控制台无错误）
- [ ] 提交前运行 `git status` 检查变更
- [ ] 提交信息清晰描述变更内容

---

*最后更新：2026-03-18*
