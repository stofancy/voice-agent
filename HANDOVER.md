# OpenClaw Voice 项目交接文档

**创建时间**: 2026-03-16 23:59
**最后更新**: 2026-03-17 00:02
**状态**: 配置已完成，等待部署测试

---

## 📋 项目概述

**目标**: 在 OpenClaw Voice 项目中集成百炼 STT/TTS，实现语音交互功能。

**架构**:
```
┌─────────────────────────────────────────────────────────┐
│  ~/workspaces/openclaw-voice/                            │
│                                                         │
│  docker-compose.yml (借鉴官方配置)                        │
│  + .env (环境变量)                                       │
│                                                         │
│  ┌────────────────────┐    ┌───────────────────────┐   │
│  │ OpenClaw Gateway   │◄──►│  OpenClaw Voice       │   │
│  │ (Port: 18789)      │    │  (Port: 8765)         │   │
│  │                    │    │                       │   │
│  │ 挂载：~/.openclaw  │    │  无挂载（环境变量）    │   │
│  │ 配置：openclaw.json│    │  STT: 百炼            │   │
│  └────────────────────┘    │  TTS: 百炼            │   │
│                            │  LLM: → Gateway       │   │
│                            └───────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**重要原则**:
- ✅ 在 `openclaw-voice` 项目中工作
- ✅ 借鉴官方 openclaw 配置方式
- ✅ **不修改**官方 `~/workspaces/openclaw/` 仓库
- ✅ Gateway 挂载 `~/.openclaw` 配置（只读）
- ✅ Voice 使用环境变量，构建自本地源码

---

## ✅ 已完成工作

### 1. 项目初始化
- ✅ Clone Purple-Horizons/openclaw-voice 到 `~/workspaces/openclaw-voice/`
- ✅ 研究 voice-agent 项目中的百炼 API 文档
- ✅ 理解 OpenClaw Voice 架构（Standalone Python 服务）

### 2. 百炼 API 集成
- ✅ `src/server/bailian_stt.py` - 百炼语音识别
  - 模型：`qwen3-asr-flash`
  - 支持 OpenAI 兼容 API
  - 支持 16kHz 音频重采样
- ✅ `src/server/bailian_tts.py` - 百炼语音合成
  - 模型：`qwen3-tts-flash`
  - 音色：Cherry（可配置）
  - 支持流式和非流式输出
- ✅ `src/server/main.py` - 主服务修改
  - 集成百炼 STT/TTS
  - 支持 Gateway 连接
  - WebSocket 消息处理

### 3. Docker 部署配置（借鉴官方）
- ✅ `docker-compose.yml` - 完整部署配置
  - 借鉴官方 `~/workspaces/openclaw/docker-compose.yml`
  - 添加 `name: openclaw-voice` 避免服务名冲突
  - Gateway 挂载 `~/.openclaw` 配置
  - Voice 构建自本地源码
- ✅ `.env.example` - 环境变量模板
  - 百炼 API Key 配置
  - 端口配置
  - 模型配置
- ✅ `start.sh` - 一键启动脚本
  - 自动创建 .env
  - 显示配置信息
  - 健康检查

### 4. 代码提交
- ✅ 15 次 Git 提交
  - `99878de` - 集成 OpenClaw Gateway 与百炼 STT/TTS
  - `022405e` - 添加 project name 避免冲突
  - `2bfe9cf` - 完全隔离部署（已废弃）
  - `5f46cba` - 创建正确的 docker-compose 配置（当前）
  - 其他修复提交

### 5. 文档
- ✅ `HANDOVER.md` - 交接文档
- ✅ `TODOS.md` - 待办事项列表
- ✅ `README.bailian.md` - 百炼 API 集成说明

---

## ❌ 未完成工作

### 1. 部署测试 ⏳ 待执行
**状态**: 配置已完成，等待部署测试

**步骤**:
```bash
cd ~/workspaces/openclaw-voice
cp .env.example .env
vim .env  # 确认百炼 API Key
./start.sh
```

**验证**:
```bash
curl http://localhost:18789/healthz  # Gateway
curl http://localhost:8765/         # Voice
```

### 2. 百炼 API Key 验证 ⏳ 待确认
**状态**: 主公提到已修正 API Key

**当前配置**:
- Key: `sk-your-api-key-here`
- 需要主公确认是否正确

### 3. 终止机制研究 ⚠️ 高优先级
**状态**: 待办事项已创建

**问题**:
- Agent 无法被中断
- 忽略停止指令
- 不响应用户请求

**待办**: `TODOS.md` 第一条

---

## 📁 文件清单

### 核心配置文件
| 文件 | 说明 | 状态 |
|------|------|------|
| `docker-compose.yml` | Docker Compose 配置 | ✅ 完成 |
| `.env.example` | 环境变量模板 | ✅ 完成 |
| `start.sh` | 启动脚本 | ✅ 完成 |

### 代码文件
| 文件 | 说明 | 状态 |
|------|------|------|
| `src/server/bailian_stt.py` | 百炼 STT | ✅ 完成 |
| `src/server/bailian_tts.py` | 百炼 TTS | ✅ 完成 |
| `src/server/main.py` | 主服务 | ✅ 完成 |
| `src/server/backend.py` | AI 后端 | ✅ 完成 |
| `Dockerfile.bailian` | Docker 镜像 | ✅ 完成 |

### 文档文件
| 文件 | 说明 | 状态 |
|------|------|------|
| `HANDOVER.md` | 交接文档 | ✅ 完成 |
| `TODOS.md` | 待办事项 | ✅ 完成 |
| `README.bailian.md` | 百炼 API 说明 | ✅ 完成 |

---

## 🔧 技术细节

### Gateway 配置（借鉴官方）
```yaml
openclaw-gateway:
  image: ghcr.io/openclaw/openclaw:latest
  volumes:
    - ~/.openclaw:/home/node/.openclaw
    - ~/.openclaw/workspace:/home/node/.openclaw/workspace
  command:
    - node
    - dist/index.js
    - gateway
    - --bind
    - lan
    - --port
    - 18789
```

### Voice 配置
```yaml
openclaw-voice:
  build:
    context: .
    dockerfile: Dockerfile.bailian
  environment:
    - ALI_BAILIAN_API_KEY=sk-sp-xxx
    - OPENCLAW_STT_MODEL=qwen3-asr-flash
    - OPENCLAW_TTS_MODEL=qwen3-tts-flash
    - OPENCLAW_GATEWAY_URL=http://openclaw-gateway:18789
    - OPENCLAW_GATEWAY_TOKEN=openclaw-your-gateway-token-here
```

### 网络配置
- Gateway 端口：18789（HTTP/WebSocket）
- Bridge 端口：18790
- Voice 端口：8765（HTTP/WebSocket）
- Project name：`openclaw-voice`
- Network：`openclaw-voice-network`

---

## 🚀 部署步骤

### 快速部署

```bash
# 1. 进入项目目录
cd ~/workspaces/openclaw-voice

# 2. 复制环境变量
cp .env.example .env

# 3. 编辑配置（确认百炼 API Key）
vim .env

# 4. 启动服务
./start.sh

# 5. 查看状态
docker compose ps

# 6. 验证服务
curl http://localhost:18789/healthz  # Gateway
curl http://localhost:8765/         # Voice
```

### 运维命令

```bash
# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 重新构建
docker compose build

# 更新部署
docker compose up -d --build
```

---

## ⚠️ 已知问题

### 1. Agent 终止机制失效
- **现象**: 不响应停止指令
- **影响**: 用户体验差，安全隐患
- **状态**: 待办事项已创建（高优先级）

### 2. 部署未测试
- **现象**: 配置已完成，但未实际部署
- **影响**: 无法验证功能
- **状态**: 等待主公确认 API Key 后部署

---

## 📊 进度总结

| 模块 | 进度 | 状态 |
|------|------|------|
| 百炼 STT 集成 | 100% | ✅ 完成 |
| 百炼 TTS 集成 | 100% | ✅ 完成 |
| Docker 配置 | 100% | ✅ 完成 |
| 部署测试 | 0% | ⏳ 待执行 |
| Voice 功能测试 | 0% | ⏳ 阻塞 |
| 终止机制研究 | 0% | ⏳ 待办（高优先级）|

**总体进度**: 约 70%（等待部署测试）

---

## 📝 交接说明

### 继续工作步骤

1. **确认百炼 API Key**
   ```bash
   cat .env | grep ALI_BAILIAN_API_KEY
   ```

2. **部署测试**
   ```bash
   cd ~/workspaces/openclaw-voice
   ./start.sh
   docker compose ps
   ```

3. **验证服务**
   ```bash
   curl http://localhost:18789/healthz
   curl http://localhost:8765/
   ```

4. **研究终止机制**（高优先级）
   - 查看 OpenClaw 源码
   - 理解中断信号处理
   - 提出修复方案

### 重要注意事项

1. **在 openclaw-voice 项目中工作**
   - 不修改 `~/workspaces/openclaw/` 官方仓库
   - 只借鉴官方配置方式

2. **Gateway 挂载主机配置**
   - `~/.openclaw` 是只读挂载
   - 不修改主机配置

3. **Voice 使用环境变量**
   - 所有配置通过 `.env` 管理
   - 不挂载主机配置

---

## 📞 联系方式

**项目位置**: `~/workspaces/openclaw-voice/`
**Git 分支**: `main`
**最后提交**: `5f46cba`

---

*文档创建：2026-03-16 23:59*
*最后更新：2026-03-17 00:02*
*下次更新：待部署测试完成后*
