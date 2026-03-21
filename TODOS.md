# OpenClaw Voice 项目待办事项

**最后更新**: 2026-03-21
**项目状态**: 🚧 开发中 - 本地/Docker 配置分离

---

## 🟡 代码优化待办 (来源: Code Review)

### 1. 统一 LLM provider 错误日志处理
**创建时间**: 2026-03-21
**状态**: 待处理
**文件**: `src/server/llm/openai_llm.py`, `src/server/llm/gemini_llm.py`

**问题**: `openai_llm.py` 有详细的错误日志提取，但 `gemini_llm.py` 没有
**建议**: 提取 HTTP 错误日志为共享工具函数

### 2. 集中化 OPENCLAW_* 环境变量常量
**创建时间**: 2026-03-21
**状态**: 待处理
**文件**: `src/server/`

**问题**: `OPENCLAW_` 前缀在代码中以字符串字面量分散使用
**建议**: 在 `src/server/constants.py` 中定义常量

---

## 🔴 高优先级

### 1. 测试流式字幕功能 ⚠️ **待测试**
**创建时间**: 2026-03-17 01:45
**状态**: 代码已完成，等待部署测试
**分支**: `feature/streaming-subtitle`

**修改内容**:
- 后端：使用 `backend.chat_stream()` 逐句发送字幕
- 前端：累积显示 `subtitle_chunk` 实现流式效果

**测试步骤**:
```bash
cd ~/workspaces/openclaw-voice
git checkout feature/streaming-subtitle
docker compose build openclaw-voice
docker compose up -d
# 访问 http://localhost:8765/ 测试语音对话
```

**优先级**: 🔴 最高
**预计耗时**: 30 分钟

---

### 2. 实现百炼 WebSocket 实时 STT ⏳ **待实现**
**创建时间**: 2026-03-17 01:45
**状态**: 待办
**参考文档**: `~/workspaces/voice-agent/语音识别 API.md`

**当前实现**: HTTP API（一次性发送完整音频）

**目标实现**: WebSocket 实时音频流 → 实时文字
- 使用 `qwen3-asr-flash` 的流式模式
- OpenAI 兼容 API：`stream=True`
- 降低延迟，边说话边识别

**修改文件**:
- `src/server/bailian_stt.py` - 添加流式识别方法
- `src/server/main.py` - 配合流式处理逻辑

**优先级**: 🔴 高
**预计耗时**: 2-3 小时

---

### 3. 实现百炼 WebSocket 实时 TTS ⏳ **待实现**
**创建时间**: 2026-03-17 01:45
**状态**: 待办
**参考文档**: `~/workspaces/voice-agent/语音合成 API.md`

**当前实现**: HTTP API（一次性合成完整文本）

**目标实现**: WebSocket 实时文字流 → 实时音频流
- 使用 `qwen3-tts-flash` 的流式模式
- DashScope SDK：`stream=True`
- 降低延迟，边生成文字边播放音频

**修改文件**:
- `src/server/bailian_tts.py` - 添加流式合成方法
- `src/server/main.py` - 配合流式处理逻辑

**优先级**: 🔴 高
**预计耗时**: 2-3 小时

---

## 🟡 中优先级

### 4. 优化启动脚本
**创建时间**: 2026-03-17 01:45
**状态**: 待优化

**当前问题**:
- 需要手动创建 Gateway 配置到 volume
- 启动脚本没有自动检测配置是否存在

**优化方案**:
```bash
# start.sh 添加自动配置生成
if ! docker run --rm -v openclaw-voice_openclaw-gateway-config:/home/node/.openclaw \
     ghcr.io/openclaw/openclaw:latest test -f /home/node/.openclaw/openclaw.json; then
  echo "⚠️  Gateway 配置不存在，正在生成..."
  # 自动生成 openclaw.json
fi
```

**优先级**: 🟡 中
**预计耗时**: 1 小时

---

### 5. 添加健康检查端点
**创建时间**: 2026-03-17 01:45
**状态**: 待实现

**需要添加**:
- `/health` - 服务健康状态
- `/ready` - 服务就绪状态
- STT/TTS/Gateway 连通性检查

**优先级**: 🟡 中
**预计耗时**: 1 小时

---

## 🟢 低优先级

### 6. 支持多音色切换
**创建时间**: 2026-03-17 01:45
**状态**: 待实现

**百炼可用音色**:
- Cherry（甜美女性）- 当前默认
- Bella（温柔女性）
- Sarah（成熟女性）
- Jack（沉稳男性）
- Allie（活泼女性）

**实现方案**:
- 前端添加音色选择器
- 后端支持动态切换音色
- 配置文件保存用户偏好

**优先级**: 🟢 低
**预计耗时**: 2 小时

---

### 7. 优化 VAD（语音活动检测）
**创建时间**: 2026-03-17 01:45
**状态**: 待优化

**当前状态**: VAD 不可用（缺少 `torch` 模块）

**优化方案**:
- 在 Dockerfile 中添加 `torch` 依赖
- 或优化 VAD 逻辑，减少误触发

**优先级**: 🟢 低
**预计耗时**: 1 小时

---

### 8. 支持连续对话模式
**创建时间**: 2026-03-17 01:45
**状态**: 待实现

**功能描述**:
- 说完一句自动开始下一句监听
- 类似 Alexa/Google Assistant 的连续对话
- 支持"退出"命令结束对话

**优先级**: 🟢 低
**预计耗时**: 2 小时

---

## ✅ 已完成任务

### 1. OpenClaw Voice 部署 ✅
**完成时间**: 2026-03-17 00:30

**成果**:
- ✅ Gateway 独立部署（端口 26523）
- ✅ Voice 服务部署（端口 8765）
- ✅ 百炼 STT 集成（qwen3-asr-flash）
- ✅ 百炼 TTS 集成（qwen3-tts-flash）
- ✅ Gateway HTTP API 启用（chatCompletions endpoint）
- ✅ 完整语音对话流程测试通过

**部署命令**:
```bash
cd ~/workspaces/openclaw-voice
./start.sh
```

### 2. 流式字幕功能（代码完成） ✅
**完成时间**: 2026-03-17 01:35

**修改内容**:
- ✅ `src/server/main.py` - 后端流式推送
- ✅ `src/client/index.html` - 前端累积显示
- ✅ Git 提交到 `feature/streaming-subtitle` 分支

**待测试**: 需要重新构建 Voice 镜像

### 3. Docker 配置优化 ✅
**完成时间**: 2026-03-17 00:55

**成果**:
- ✅ 使用独立 Docker volume（不挂载 `~/.openclaw`）
- ✅ 手动创建 Gateway 配置到 volume
- ✅ 启用 HTTP API endpoint（chatCompletions）
- ✅ 配置百炼模型（bailian/qwen3-coder-next）

### 4. 文档和记录 ✅
**完成时间**: 2026-03-17 01:45

**成果**:
- ✅ `memory/2026-03-17.md` - 详细工作日志
- ✅ `MEMORY.md` - 更新长期记忆
- ✅ `TODOS.md` - 更新待办事项

---

## 📊 进度概览

| 模块 | 进度 | 状态 |
|------|------|------|
| 百炼 STT 集成 | 100% | ✅ 完成 |
| 百炼 TTS 集成 | 100% | ✅ 完成 |
| Docker 部署 | 100% | ✅ 完成 |
| Gateway 配置 | 100% | ✅ 完成 |
| 流式字幕（代码） | 100% | ✅ 完成 |
| 流式字幕（测试） | 0% | ⏳ 待测试 |
| 百炼实时 STT | 0% | ⏳ 待实现 |
| 百炼实时 TTS | 0% | ⏳ 待实现 |

**总体进度**: 约 75%（等待流式字幕测试和实时 API 实现）

---

## 📝 备注

- **当前状态**: 部署完成，基础功能正常
- **下一步**: 测试流式字幕功能
- **长期目标**: 实现百炼 WebSocket 实时 API 降低延迟

---

*最后更新：2026-03-17 01:45*
*下次更新：待流式字幕测试完成后*
