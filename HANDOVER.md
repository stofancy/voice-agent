# OpenClaw Voice 项目交接文档

**创建时间**: 2026-03-16 23:47
**最后更新**: 2026-03-16 23:47
**状态**: 暂停（等待终止机制研究完成）

---

## 📋 项目概述

**目标**: 在 OpenClaw Voice 项目中集成百炼 STT/TTS，实现语音交互功能。

**架构**:
```
┌─────────────────────────────────────────────────────────┐
│  Docker Compose (project: openclaw-voice)               │
│                                                         │
│  ┌────────────────────┐    ┌───────────────────────┐   │
│  │ OpenClaw Gateway   │◄──►│  OpenClaw Voice       │   │
│  │ (Port: 18789)      │    │  (Port: 8765)         │   │
│  │                    │    │                       │   │
│  │ - 独立实例         │    │  - STT: 百炼          │   │
│  │ - 不触碰主机配置   │    │  - TTS: 百炼          │   │
│  │ - volume 隔离      │    │  - LLM: → Gateway     │   │
│  └────────────────────┘    └───────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

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

### 3. Docker 部署配置
- ✅ `docker-compose.full.yml` - 完整部署配置
  - 借鉴官方 OpenClaw docker-compose.yml
  - 添加 `name: openclaw-voice` 避免服务名冲突
  - 使用独立 volume（不挂载主机配置）
  - Gateway 命令：`node openclaw.mjs gateway --allow-unconfigured`
- ✅ `.env.full` - 环境变量模板
  - 百炼 API Key 配置
  - 端口配置
  - 模型配置
- ✅ `start-full.sh` - 一键启动脚本
  - 自动创建 .env
  - 显示配置信息
  - 健康检查

### 4. 配置修复
- ✅ 移除所有 `~/.openclaw` 配置挂载（违背原则）
- ✅ 使用独立 Docker volume（`openclaw-gateway-data`）
- ✅ 修正 Gateway 命令（`dist/index.js` → `openclaw.mjs`）
- ✅ 添加 `--allow-unconfigured` 参数
- ✅ 增加健康检查宽限期（20s → 60s）

### 5. 代码提交
- ✅ 7 次 Git 提交
  - `99878de` - 集成 OpenClaw Gateway 与百炼 STT/TTS
  - `022405e` - 添加 project name 避免冲突
  - `2bfe9cf` - 完全隔离部署
  - `7643249` - 添加待办事项
  - 其他修复提交

### 6. 问题记录
- ✅ 记录所有遇到的问题和解决方案
- ✅ 更新 `memory/2026-03-16.md`
- ✅ 创建 `TODOS.md` 待办事项列表

---

## ❌ 未完成工作

### 1. Gateway 启动问题 🔴 阻塞中
**状态**: Gateway 无法启动（exit 137）

**已尝试方案**:
- 修正 Gateway 命令
- 添加 `--allow-unconfigured` 参数
- 增加健康检查宽限期
- 检查内存（充足：15GB）

**可能原因**:
- Gateway 初始化超时
- 镜像问题
- 配置问题

**下一步**:
- 需要更多日志分析
- 可能需要调整 Gateway 配置
- 或测试简化启动方式

### 2. 百炼 API Key 验证 ⏳ 待确认
**状态**: 主公提到已修正 API Key

**当前配置**:
- Key: `REDACTED-gateway-provider-key`
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

### 核心文件
| 文件 | 说明 | 状态 |
|------|------|------|
| `docker-compose.full.yml` | Docker Compose 配置 | ✅ 完成 |
| `.env.full` | 环境变量模板 | ✅ 完成 |
| `start-full.sh` | 启动脚本 | ✅ 完成 |
| `TODOS.md` | 待办事项列表 | ✅ 完成 |
| `README.bailian.md` | 使用文档 | ⚠️ 需更新 |

### 代码文件
| 文件 | 说明 | 状态 |
|------|------|------|
| `src/server/bailian_stt.py` | 百炼 STT | ✅ 完成 |
| `src/server/bailian_tts.py` | 百炼 TTS | ✅ 完成 |
| `src/server/main.py` | 主服务 | ✅ 完成 |
| `src/server/backend.py` | AI 后端 | ✅ 完成 |
| `Dockerfile.bailian` | Docker 镜像 | ✅ 完成 |

### 配置文件
| 文件 | 说明 | 状态 |
|------|------|------|
| `requirements.txt` | Python 依赖 | ✅ 完成 |
| `.env` | 环境变量（运行时） | ⚠️ 需主公确认 |

---

## 🔧 技术细节

### Gateway 配置
```yaml
command:
  - "node"
  - "openclaw.mjs"
  - "gateway"
  - "--allow-unconfigured"
  - "--bind"
  - "lan"
  - "--port"
  - "18789"
```

### Voice 配置
```yaml
environment:
  - ALI_BAILIAN_API_KEY=REDACTED-gateway-provider-key
  - OPENCLAW_STT_MODEL=qwen3-asr-flash
  - OPENCLAW_TTS_MODEL=qwen3-tts-flash
  - OPENCLAW_TTS_VOICE=Cherry
  - OPENCLAW_GATEWAY_URL=http://openclaw-gateway:18789
  - OPENCLAW_GATEWAY_TOKEN=REDACTED-openclaw-voice-token
```

### 网络配置
- Gateway 端口：18789（HTTP/WebSocket）
- Bridge 端口：18790
- Voice 端口：8765（HTTP/WebSocket）
- Project name：`openclaw-voice`

---

## ⚠️ 已知问题

### 1. Gateway 启动失败
- **现象**: exit 137（可能被 kill）
- **影响**: Voice 无法连接 Gateway
- **状态**: 调试中

### 2. Agent 终止机制失效
- **现象**: 不响应停止指令
- **影响**: 用户体验差，安全隐患
- **状态**: 待办事项已创建

### 3. Docker Compose 命令
- **现象**: `docker compose` vs `docker-compose` 不一致
- **影响**: 脚本可能失败
- **状态**: 脚本已适配两种情况

---

## 📝 交接说明

### 继续工作步骤

1. **确认百炼 API Key**
   ```bash
   cat ~/workspaces/openclaw-voice/.env | grep ALI_BAILIAN_API_KEY
   ```

2. **调试 Gateway 启动**
   ```bash
   cd ~/workspaces/openclaw-voice
   docker compose -f docker-compose.full.yml -p openclaw-voice up -d
   docker compose -f docker-compose.full.yml -p openclaw-voice logs openclaw-gateway
   ```

3. **研究终止机制**（高优先级）
   - 查看 OpenClaw 源码
   - 理解中断信号处理
   - 提出修复方案

4. **测试 Voice 功能**
   ```bash
   # 访问 Voice UI
   http://localhost:8765/
   
   # 测试 STT
   # 测试 TTS
   # 测试 Gateway 连接
   ```

### 重要注意事项

1. **绝对不要**挂载 `~/.openclaw` 配置目录
2. **必须使用** project name 避免冲突
3. **Gateway 命令**必须使用 `node openclaw.mjs gateway`
4. **健康检查**宽限期至少 60 秒

---

## 📊 进度总结

| 模块 | 进度 | 状态 |
|------|------|------|
| 百炼 STT 集成 | 100% | ✅ 完成 |
| 百炼 TTS 集成 | 100% | ✅ 完成 |
| Docker 配置 | 100% | ✅ 完成 |
| Gateway 启动 | 0% | ❌ 失败 |
| Voice 测试 | 0% | ⏳ 阻塞 |
| 终止机制研究 | 0% | ⏳ 待办 |

**总体进度**: 约 60%（Gateway 启动问题阻塞后续测试）

---

## 📞 联系方式

**项目位置**: `~/workspaces/openclaw-voice/`
**Git 分支**: `main`
**最后提交**: `7643249`

---

*文档创建：2026-03-16 23:47*
*下次更新：待 Gateway 问题解决后*
