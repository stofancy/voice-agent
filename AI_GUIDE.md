# AI 助手快速指南 🤖

**欢迎使用 OpenClaw Voice 项目进行开发！**

本项目已配置为支持多种 AI 编程助手自动读取开发规范。

---

## 🚀 一键启动开发环境

```bash
cd ~/workspaces/voice-agent
./scripts/dev-all.sh
```

**访问地址**：
- 前端：http://localhost:5173/v2/
- 后端 API：http://localhost:8766/
- 健康检查：http://localhost:8766/health

---

## 📁 AI 配置文件位置

| AI 工具 | 配置文件 | 自动读取 |
|---------|----------|----------|
| **GitHub Copilot** | `.github/copilot-instructions.md` | ✅ |
| **Claude Code** | `.claude/instructions.md` | ✅ |
| **OpenClaw** | `.openclaw/skills/voice-agent-dev/SKILL.md` | ✅ |
| **通用 AI** | `docs/AI_DEV_GUIDE.md` | ✅ |
| **所有工具** | `AI_GUIDE.md` (本文件) | ✅ |

---

## 📋 核心脚本

| 脚本 | 用途 |
|------|------|
| `./scripts/dev-all.sh` | 启动所有开发服务 |
| `./scripts/dev-backend.sh` | 仅启动后端 |
| `./scripts/dev-frontend.sh` | 仅启动前端 |
| `./scripts/deploy.sh` | 生产部署 |
| `./scripts/stop-all.sh` | 停止所有服务 |

---

## 🎯 端口分配

| 服务 | 开发 | 生产 |
|------|------|------|
| 后端 | 8766 | 8765 |
| 前端 | 5173 | 8764 |
| Gateway | 26523 | 26523 |

---

## 📖 完整文档

- **`docs/DEVELOPMENT.md`** - 详细开发指南
- **`docs/AI_DEV_GUIDE.md`** - AI 助手专用指南
- **`README.md`** - 项目概述

---

*最后更新：2026-03-18*
