# Docker 挂载方案迁移指南

**创建时间**: 2026-03-17 23:48
**状态**: 待执行
**优先级**: 🟡 中

---

## 📊 当前架构

### 现状
```yaml
volumes:
  - openclaw-gateway-config:/home/node/.openclaw

volumes:
  openclaw-gateway-config:  # Docker managed volume
```

**特点**:
- ✅ Docker 自动管理 volume
- ✅ 数据持久化
- ❌ 文件在 Docker 内部，不易访问和修改
- ❌ 需要 `docker volume inspect` 查看位置

**当前 Volume 位置**:
```bash
$ docker volume inspect openclaw-voice_openclaw-gateway-config
[
  {
    "Driver": "local",
    "Mountpoint": "/var/lib/docker/volumes/openclaw-voice_openclaw-gateway-config/_data",
    ...
  }
]
```

---

## 🎯 目标架构

### 新方案
```yaml
volumes:
  - ~/voice-agent-data/openclaw-gateway:/home/node/.openclaw
```

**特点**:
- ✅ Bind mount（主机目录映射）
- ✅ 文件在 `~/voice-agent-data/` 可直接访问
- ✅ 方便查看、修改、备份
- ✅ 迁移后数据不丢失

---

## 📋 迁移步骤（保证数据不丢失）

### Step 1: 查看当前 Volume 内容

```bash
# 确认 volume 存在
docker volume ls | grep openclaw-voice

# 查看 volume 详细信息
docker volume inspect openclaw-voice_openclaw-gateway-config

# 临时容器查看内容
docker run --rm -v openclaw-voice_openclaw-gateway-config:/data alpine ls -la /data
```

### Step 2: 创建新目录

```bash
# 创建目标目录
mkdir -p ~/voice-agent-data/openclaw-gateway

# 确认目录创建成功
ls -la ~/voice-agent-data/
```

### Step 3: 导出 Volume 内容到新目录

**方法 A: 使用临时容器（推荐）**

```bash
# 停止服务
cd ~/workspaces/voice-agent
docker compose down

# 导出 volume 内容
docker run --rm \
  -v openclaw-voice_openclaw-gateway-config:/source \
  -v ~/voice-agent-data/openclaw-gateway:/target \
  alpine \
  cp -a /source/. /target/

# 验证复制结果
echo "=== Source ===" && docker run --rm -v openclaw-voice_openclaw-gateway-config:/source alpine ls -la /source
echo "=== Target ===" && ls -la ~/voice-agent-data/openclaw-gateway/
```

**方法 B: 使用 docker cp**

```bash
# 创建临时容器
docker create --name temp-export -v openclaw-voice_openclaw-gateway-config:/data alpine

# 导出文件
docker export temp-export | tar -xf - -C ~/voice-agent-data/openclaw-gateway/

# 清理临时容器
docker rm temp-export
```

### Step 4: 更新 docker-compose.yml

**修改前**:
```yaml
volumes:
  - openclaw-gateway-config:/home/node/.openclaw

volumes:
  openclaw-gateway-config:
```

**修改后**:
```yaml
volumes:
  - ${OPENCLAW_DATA_DIR:-~/voice-agent-data/openclaw-gateway}:/home/node/.openclaw

# 注释掉 volume 定义（不再需要 Docker managed volume）
# volumes:
#   openclaw-gateway-config:
```

**或者使用绝对路径**:
```yaml
volumes:
  - /home/ztmdsbt/voice-agent-data/openclaw-gateway:/home/node/.openclaw
```

### Step 5: 重启服务并验证

```bash
# 启动服务
docker compose up -d

# 检查服务状态
docker compose ps

# 查看日志
docker compose logs openclaw-gateway

# 验证数据可访问
ls -la ~/voice-agent-data/openclaw-gateway/workspace/

# 测试修改文件
echo "test" >> ~/voice-agent-data/openclaw-gateway/workspace/test.txt
docker compose exec openclaw-gateway cat /home/node/.openclaw/workspace/test.txt
```

### Step 6: 清理旧 Volume（可选）

**⚠️ 仅在验证新方案正常运行后执行！**

```bash
# 确认服务正常运行
docker compose ps  # 所有服务应为 "Up" 状态

# 备份旧 volume（可选）
docker run --rm \
  -v openclaw-voice_openclaw-gateway-config:/source \
  -v ~/voice-agent-data/backup-old-volume:/backup \
  alpine \
  tar -czf /backup/old-volume-backup.tar.gz -C /source .

# 删除旧 volume
docker volume rm openclaw-voice_openclaw-gateway-config

# 验证删除
docker volume ls | grep openclaw-voice
```

---

## 🔍 验证清单

迁移完成后，请确认以下项目：

- [ ] `docker compose ps` 显示所有服务为 "Up"
- [ ] Gateway 日志无错误
- [ ] Voice 服务可连接 Gateway
- [ ] `~/voice-agent-data/openclaw-gateway/workspace/` 包含原有文件
- [ ] 修改主机文件后，容器内可见
- [ ] Web UI 可正常访问
- [ ] 原有配置（API Key、技能等）仍然有效

---

## 🚨 回滚方案

如新方案出现问题，可快速回滚：

```bash
# 停止服务
docker compose down

# 恢复 docker-compose.yml（使用 git 或手动修改）
git checkout docker-compose.yml

# 确认 volume 仍存在
docker volume ls | grep openclaw-voice

# 重启服务
docker compose up -d
```

---

## 📝 补充说明

### 为什么使用 `~/voice-agent-data/` 而不是 `~/.openclaw/`？

1. **清晰的项目边界** - voice-agent 的数据独立于主 OpenClaw 实例
2. **避免冲突** - 不与主机 `~/.openclaw/` 配置混淆
3. **易于备份** - 整个项目数据在一个目录
4. **Docker 友好** - 路径简单，无权限问题

### 目录结构预期

```
~/voice-agent-data/
└── openclaw-gateway/
    └── .openclaw/
        ├── workspace/          # 工作空间（技能、文档等）
        ├── openclaw.json       # 配置文件
        ├── credentials.json    # 凭证（如有）
        └── ...
```

---

## ⏱️ 预计耗时

- Step 1-2: 5 分钟
- Step 3: 5 分钟
- Step 4: 5 分钟
- Step 5: 10 分钟
- Step 6: 5 分钟（可选）

**总计**: 约 30 分钟

---

## 📚 相关文档

- Docker Volume 文档：https://docs.docker.com/storage/volumes/
- Bind Mount 文档：https://docs.docker.com/storage/bind-mounts/
- docker-compose volume 文档：https://docs.docker.com/compose/compose-file/05-services/#volumes

---

*文档创建时间：2026-03-17 23:48*
*作者：九章*
