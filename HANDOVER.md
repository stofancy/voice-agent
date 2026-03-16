# OpenClaw Voice 项目交接文档

**创建时间**: 2026-03-16 23:59
**最后更新**: 2026-03-17 00:05
**状态**: 配置已完成，等待部署测试

---

## 📋 项目概述

**目标**: 在 OpenClaw Voice 项目中集成百炼 STT/TTS，实现语音交互功能。

**架构**:
```
┌─────────────────────────────────────────────────────────┐
│  ~/workspaces/openclaw-voice/                            │
│                                                         │
│  docker-compose.yml + .env                               │
│                                                         │
│  ┌────────────────────┐    ┌───────────────────────┐   │
│  │ OpenClaw Gateway   │◄──►│  OpenClaw Voice       │   │
│  │ (Port: 18789)      │    │  (Port: 8765)         │   │
│  │                    │    │                       │   │
│  │ 独立 volume 配置     │    │  无挂载（环境变量）    │   │
│  │ 不触碰 ~/.openclaw │    │  STT: 百炼            │   │
│  └────────────────────┘    │  TTS: 百炼            │   │
│                            │  LLM: → Gateway       │   │
│                            └───────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**重要原则**:
- ✅ 在 `openclaw-voice` 项目中工作
- ✅ 借鉴官方 docker-compose 配置方式
- ✅ **不修改**官方 `~/workspaces/openclaw/` 仓库
- ✅ **不挂载** `~/.openclaw`（主公的本地配置）
- ✅ Gateway 使用独立 Docker volume
- ✅ Voice 使用环境变量，构建自本地源码

---

## ✅ 已完成工作

### 1. 百炼 API 集成
- ✅ `src/server/bailian_stt.py` - 百炼语音识别（qwen3-asr-flash）
- ✅ `src/server/bailian_tts.py` - 百炼语音合成（qwen3-tts-flash）
- ✅ `src/server/main.py` - 主服务（集成 STT/TTS + Gateway 连接）

### 2. Docker 部署配置（借鉴官方）
- ✅ `docker-compose.yml` - 完整部署配置
  - Gateway 使用独立 volume（`openclaw-gateway-config`）
  - **不挂载** `~/.openclaw`
  - 使用 `--allow-unconfigured` 模式
  - Voice 构建自本地源码
- ✅ `.env.example` - 环境变量模板
- ✅ `start.sh` - 一键启动脚本

### 3. 代码提交
- ✅ 17 次 Git 提交（最新：`55650a7`）

---

## ❌ 未完成工作

### 1. 部署测试 ⏳ 待执行
**步骤**:
```bash
cd ~/workspaces/openclaw-voice
cp .env.example .env
vim .env  # 确认百炼 API Key
docker compose up -d
```

### 2. 百炼 API Key 验证 ⏳ 待确认
- Key: `YOUR_BAILIAN_API_KEY`

### 3. 终止机制研究 ⚠️ 高优先级
- Agent 无法被中断
- 待办：`TODOS.md` 第一条

---

## 🚀 部署步骤

```bash
# 1. 进入项目目录
cd ~/workspaces/openclaw-voice

# 2. 复制环境变量
cp .env.example .env

# 3. 编辑配置（确认百炼 API Key）
vim .env

# 4. 启动服务
docker compose up -d

# 5. 验证
curl http://localhost:18789/healthz  # Gateway
curl http://localhost:8765/         # Voice
```

---

## ⚠️ 核心原则

1. **在 openclaw-voice 项目中工作** - 不修改官方仓库
2. **不挂载 ~/.openclaw** - 使用独立 Docker volume
3. **借鉴官方配置方式** - 通过 .env 传递环境变量

---

*最后更新：2026-03-17 00:05*
