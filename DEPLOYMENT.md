# OpenClaw Voice 部署指南

**最后更新**: 2026-03-16 23:59

---

## 📋 部署架构

OpenClaw Voice 与 OpenClaw Gateway **统一部署**在同一个 Docker Compose 配置中。

```
┌─────────────────────────────────────────────────────────────┐
│  ~/workspaces/openclaw/                                      │
│                                                              │
│  docker-compose.voice.yml                                    │
│  + .env.voice                                                │
│                                                              │
│  ┌────────────────────┐    ┌───────────────────────┐        │
│  │ OpenClaw Gateway   │◄──►│  OpenClaw Voice       │        │
│  │ (Port: 18789)      │    │  (Port: 8765)         │        │
│  │                    │    │                       │        │
│  │ 挂载：~/.openclaw  │    │  无挂载（环境变量）    │        │
│  └────────────────────┘    └───────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速部署

### 前提条件

1. Docker 和 Docker Compose 已安装
2. OpenClaw 已配置（`~/.openclaw/openclaw.json` 存在）
3. 百炼 API Key 已获取

### 部署步骤

```bash
# 1. 进入 OpenClaw 项目目录
cd ~/workspaces/openclaw

# 2. 复制环境变量配置
cp .env.voice .env

# 3. 编辑配置（确认百炼 API Key）
vim .env

# 4. 启动服务
docker compose -f docker-compose.voice.yml up -d

# 5. 查看状态
docker compose -f docker-compose.voice.yml ps

# 6. 查看日志
docker compose -f docker-compose.voice.yml logs -f
```

### 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| Gateway | http://localhost:18789/ | OpenClaw Gateway API |
| Voice | http://localhost:8765/ | OpenClaw Voice UI |

---

## ⚙️ 配置说明

### 环境变量（.env.voice）

```bash
# Gateway 配置
OPENCLAW_GATEWAY_BIND=lan
OPENCLAW_GATEWAY_PORT=18789
OPENCLAW_BRIDGE_PORT=18790
OPENCLAW_GATEWAY_TOKEN=REDACTED-openclaw-voice-token

# 百炼 API Key（必须正确配置）
ALI_BAILIAN_API_KEY=REDACTED-gateway-provider-key

# Voice 配置
OPENCLAW_VOICE_PORT=8765
OPENCLAW_STT_MODEL=qwen3-asr-flash
OPENCLAW_TTS_MODEL=qwen3-tts-flash
OPENCLAW_TTS_VOICE=Cherry
```

### Docker Compose 配置（docker-compose.voice.yml）

**Gateway 服务**:
- 镜像：`ghcr.io/openclaw/openclaw:latest`
- 挂载：`~/.openclaw`（配置目录）
- 端口：18789（Gateway）、18790（Bridge）
- 命令：`node dist/index.js gateway --bind lan --port 18789`

**Voice 服务**:
- 构建：`~/workspaces/openclaw-voice/Dockerfile.bailian`
- 挂载：无（使用环境变量）
- 端口：8765
- 连接 Gateway：`http://openclaw-gateway:18789`

---

## 🔧 运维命令

```bash
# 查看状态
docker compose -f docker-compose.voice.yml ps

# 查看日志
docker compose -f docker-compose.voice.yml logs -f openclaw-gateway
docker compose -f docker-compose.voice.yml logs -f openclaw-voice

# 重启服务
docker compose -f docker-compose.voice.yml restart

# 停止服务
docker compose -f docker-compose.voice.yml down

# 重新构建 Voice
docker compose -f docker-compose.voice.yml build openclaw-voice

# 更新部署
docker compose -f docker-compose.voice.yml up -d --build
```

---

## 📁 项目结构

### OpenClaw 项目（`~/workspaces/openclaw/`）

```
openclaw/
├── docker-compose.yml          # 官方配置
├── docker-compose.voice.yml    # Voice 集成配置 ⭐
├── .env.voice                  # Voice 环境变量
├── .env.example                # 环境变量模板
└── ...
```

### OpenClaw Voice 项目（`~/workspaces/openclaw-voice/`）

```
openclaw-voice/
├── Dockerfile.bailian          # Voice Docker 镜像
├── requirements.txt            # Python 依赖
├── src/
│   └── server/
│       ├── main.py             # 主服务
│       ├── bailian_stt.py      # 百炼 STT
│       ├── bailian_tts.py      # 百炼 TTS
│       └── backend.py          # AI 后端
└── ...
```

---

## ⚠️ 重要注意事项

### 1. 配置目录挂载

**Gateway 必须挂载 `~/.openclaw`**：
- 这是 OpenClaw 的官方配置方式
- Gateway 需要读取 `openclaw.json` 配置
- **不要**在 Voice 项目中挂载主机配置

**Voice 不挂载任何配置**：
- Voice 使用环境变量配置
- 所有配置通过 `.env.voice` 管理
- 保持 Voice 项目的独立性

### 2. 网络连接

Voice 通过 Docker network 连接 Gateway：
```yaml
environment:
  - OPENCLAW_GATEWAY_URL=http://openclaw-gateway:18789
  - OPENCLAW_GATEWAY_TOKEN=REDACTED-openclaw-voice-token
```

**不要使用 `localhost`**，应该使用服务名 `openclaw-gateway`。

### 3. 百炼 API Key

确保 API Key 正确且有足够额度：
- STT: `qwen3-asr-flash`
- TTS: `qwen3-tts-flash`
- 需要开通语音识别和语音合成服务

---

## 🐛 故障排查

### Gateway 无法启动

```bash
# 查看日志
docker compose -f docker-compose.voice.yml logs openclaw-gateway

# 检查配置
cat ~/.openclaw/openclaw.json

# 验证端口
lsof -i :18789
```

### Voice 无法连接 Gateway

```bash
# 测试 Gateway 连通性
curl http://localhost:18789/healthz

# 查看 Voice 日志
docker compose -f docker-compose.voice.yml logs openclaw-voice

# 检查环境变量
docker compose -f docker-compose.voice.yml exec openclaw-voice env | grep GATEWAY
```

### 百炼 API 调用失败

```bash
# 验证 API Key
docker compose -f docker-compose.voice.yml exec openclaw-voice env | grep ALI_BAILIAN

# 测试 STT
curl -X POST http://localhost:8765/stt ...

# 测试 TTS
curl -X POST http://localhost:8765/tts ...
```

---

## 📝 开发模式

### 本地开发 Voice

```bash
# 1. 在 openclaw-voice 项目中
cd ~/workspaces/openclaw-voice

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置环境变量
export ALI_BAILIAN_API_KEY=sk-sp-xxx
export OPENCLAW_GATEWAY_URL=http://localhost:18789
export OPENCLAW_GATEWAY_TOKEN=REDACTED-openclaw-voice-token

# 4. 启动开发服务器
python -m uvicorn src.server.main:app --reload --port 8765
```

### 只启动 Gateway

```bash
cd ~/workspaces/openclaw
docker compose up -d openclaw-gateway
```

### 只启动 Voice（需要 Gateway 已运行）

```bash
cd ~/workspaces/openclaw
docker compose -f docker-compose.voice.yml up -d openclaw-voice
```

---

## 📚 相关文档

| 文档 | 说明 |
|------|------|
| [README.bailian.md](README.bailian.md) | 百炼 API 集成说明 |
| [HANDOVER.md](HANDOVER.md) | 项目交接文档 |
| [TODOS.md](TODOS.md) | 待办事项列表 |

---

*最后更新：2026-03-16 23:59*
*部署方式：Docker Compose 统一部署*
