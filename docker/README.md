# Voice Agent Plugin - Docker 部署

## 🚀 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，确认 API Key 正确
```

### 2. 构建镜像

```bash
docker-compose build
```

### 3. 启动服务

```bash
docker-compose up -d
```

### 4. 查看日志

```bash
docker-compose logs -f
```

### 5. 访问服务

- **WebUI**: http://localhost:5182
- **WebSocket**: ws://localhost:8774/voice-agent/stream

---

## 📋 端口说明

| 端口 | 用途 | 默认值 |
|------|------|--------|
| `WEBUI_PORT` | WebUI 访问 | 5182 |
| `WS_PORT` | WebSocket 服务器 | 8774 |

---

## 🔧 常用命令

```bash
# 查看状态
docker-compose ps

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 重新构建
docker-compose build --no-cache

# 查看日志
docker-compose logs -f voice-agent

# 进入容器
docker-compose exec voice-agent bash
```

---

## 📊 健康检查

```bash
# 检查容器健康状态
docker inspect voice-agent-plugin --format='{{.State.Health.Status}}'

# 查看健康检查日志
docker inspect voice-agent-plugin --format='{{json .State.Health}}' | jq
```

---

## 🔍 故障排查

### 插件未加载

```bash
# 检查插件目录
docker-compose exec voice-agent ls -la /home/node/.openclaw/extensions/voice-agent/dist/

# 查看 Gateway 日志
docker-compose logs voice-agent | grep -E "voice-agent|Plugin|Error"
```

### 端口冲突

```bash
# 检查端口占用
lsof -i :5182
lsof -i :8774

# 修改 .env 中的端口
WEBUI_PORT=5183
WS_PORT=8775
```

---

## 📝 数据持久化

配置和数据存储在 Docker volume `voice-agent-data` 中：

```bash
# 查看 volume 位置
docker volume inspect voice-agent-data

# 备份配置
docker run --rm -v voice-agent-data:/data -v $(pwd):/backup alpine tar czf /backup/voice-agent-config.tar.gz /data
```

---

## 🎯 架构说明

```
┌─────────────────────────────────────┐
│   Voice Agent Plugin Container      │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  OpenClaw Gateway             │  │
│  │                               │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  Voice Agent Plugin     │  │  │
│  │  │  - WebSocket Server     │  │  │
│  │  │  - STT Client           │  │  │
│  │  │  - TTS Client           │  │  │
│  │  │  - Agent Integration    │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
│                                     │
│  Ports: 5173 (WebUI), 8765 (WS)    │
└─────────────────────────────────────┘
           │              │
           │              │
    http://localhost:5182  ws://localhost:8774
```
