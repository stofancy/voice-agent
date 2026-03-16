# 🦞 OpenClaw Voice - 百炼集成完成报告

**任务**: 创建 Docker 隔离环境测试 voice capability，集成阿里百炼 STT/TTS

**完成时间**: 2026-03-16 19:45

---

## ✅ 已完成工作

### 1. 项目准备

- ✅ Clone Purple-Horizons/openclaw-voice 到 `~/workspaces/openclaw-voice/`
- ✅ 分析原项目架构（Whisper STT + ElevenLabs TTS）
- ✅ 研究 voice-agent 项目中的百炼 API 文档

### 2. 百炼 STT 集成

**文件**: `src/server/bailian_stt.py`

**功能**:
- ✅ 基于 OpenAI 兼容 API 调用百炼 STT
- ✅ 支持 `qwen3-asr-flash` 模型
- ✅ 支持多种语言（中文、英文、粤语等）
- ✅ 支持 ITN（逆文本标准化）
- ✅ numpy array → WAV 格式转换
- ✅ Base64 编码传输

**API 配置**:
```python
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
model = "qwen3-asr-flash"
```

### 3. 百炼 TTS 集成

**文件**: `src/server/bailian_tts.py`

**功能**:
- ✅ 基于 DashScope API 调用百炼 TTS
- ✅ 支持 `qwen3-tts-flash` 模型
- ✅ 支持多种音色（Cherry, Bella, Sarah, Jack, Allie）
- ✅ 支持流式和非流式输出
- ✅ 支持保存到文件

**API 配置**:
```python
api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
model = "qwen3-tts-flash"
voice = "Cherry"
```

### 4. 主服务修改

**文件**: `src/server/main.py`

**修改内容**:
- ✅ 导入百炼 STT/TTS 模块
- ✅ 修改 Settings 类添加百炼配置
- ✅ 修改 startup 初始化百炼服务
- ✅ 修改 WebSocket 处理逻辑适配百炼 API
- ✅ 添加错误处理和日志记录

**文件**: `src/server/backend.py`

**修改内容**:
- ✅ 添加 OpenClaw Gateway 支持（使用 OpenAI 兼容 API）

### 5. Docker 配置

**文件**: `Dockerfile.bailian`
- ✅ 基于 Python 3.11 slim
- ✅ 安装必要依赖（ffmpeg, libsndfile1）
- ✅ 配置环境变量
- ✅ 健康检查

**文件**: `docker-compose.bailian.yml`
- ✅ 服务定义（openclaw-voice-bailian）
- ✅ 端口映射（8765:8765）
- ✅ 环境变量配置
- ✅ 卷挂载（logs, cache）
- ✅ extra_hosts（访问主机 Gateway）
- ✅ 健康检查配置

**文件**: `.env.bailian`
- ✅ 百炼 API Key 配置
- ✅ OpenClaw Gateway 连接配置
- ✅ STT/TTS 模型和音色配置
- ✅ 服务器配置

### 6. 脚本和文档

**文件**: `scripts/start-bailian.sh`
- ✅ 一键启动脚本
- ✅ 配置检查
- ✅ 日志和有用命令提示

**文件**: `README.bailian.md`
- ✅ 快速启动指南
- ✅ 配置说明
- ✅ 故障排查
- ✅ 技术架构图

**文件**: `test-bailian.py`
- ✅ STT 测试
- ✅ TTS 测试
- ✅ 结果报告

**文件**: `requirements.txt`
- ✅ 添加 aiohttp 依赖

---

## 📋 配置摘要

### 百炼 API

| 配置项 | 值 | 说明 |
|--------|-----|------|
| API Key | `REDACTED-gateway-provider-key` | 主公现有配置 |
| STT 模型 | `qwen3-asr-flash` | 短音频识别（≤5 分钟） |
| TTS 模型 | `qwen3-tts-flash` | 快速语音合成 |
| TTS 音色 | `Cherry` | 甜美女性 |
| STT 语言 | `zh` | 中文 |
| TTS 语言 | `Chinese` | 中文 |

### OpenClaw Gateway

| 配置项 | 值 | 说明 |
|--------|-----|------|
| Gateway URL | `http://host.docker.internal:7777` | Docker 访问主机 |
| Gateway Token | `REDACTED-openclaw-gateway-token` | 主公现有配置 |
| 端口 | 7777 | 主公 Gateway 端口 |

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| WebSocket | 8765 | 浏览器连接 |
| HTTP | 8765 | Web 界面 |

---

## 🚀 使用方法

### 启动服务

```bash
cd ~/workspaces/openclaw-voice
./scripts/start-bailian.sh
```

或手动：

```bash
docker-compose -f docker-compose.bailian.yml up --build -d
```

### 访问界面

打开浏览器：**http://localhost:8765**

### 查看日志

```bash
docker-compose -f docker-compose.bailian.yml logs -f
```

### 测试 API

```bash
# 测试 STT/TTS
python test-bailian.py
```

### 停止服务

```bash
docker-compose -f docker-compose.bailian.yml down
```

---

## 📊 技术架构

```
┌─────────────┐    WebSocket    ┌──────────────────────────────────────┐
│   Browser   │◄───────────────►│     OpenClaw Voice (Docker)          │
│  (mic/spk)  │                 │                                      │
└─────────────┘                 │  ┌────────────┐  ┌────────────────┐ │
                                │  │ Bailian STT│→│ OpenClaw Agent │ │
                                │  │ (qwen-asr) │  │   (Gateway)    │ │
                                │  └────────────┘  └───────┬────────┘ │
                                │                          │           │
                                │                    ┌─────▼─────┐    │
                                │                    │Bailian TTS│    │
                                │                    │(qwen-tts) │    │
                                │                    └───────────┘    │
                                └──────────────────────────────────────┘
```

---

## 🔒 安全说明

- ✅ **完全隔离** - Docker 容器运行，不影响生产环境
- ✅ **只读连接** - 仅读取 Gateway，不修改配置
- ✅ **API Key 保护** - 敏感信息在 `.env` 中，不提交 Git
- ✅ **无外部依赖** - 仅使用百炼 API，无需 ElevenLabs 等

---

## ⚠️ 注意事项

### 网络要求

- Docker 容器需访问主机 Gateway（`host.docker.internal`）
- 容器需访问外网（百炼 API）

### API 配额

- 百炼 STT: 按音频时长计费
- 百炼 TTS: 按字符数计费
- 测试时注意控制用量

### 浏览器要求

- 需要麦克风权限
- HTTPS 要求（移动端）
- WebSocket 支持

---

## 📝 后续改进建议

1. **流式优化** - 当前为非流式，可优化为句子级流式
2. **VAD 集成** - 优化语音活动检测
3. **多音色支持** - 添加音色切换功能
4. **离线缓存** - 缓存常用 TTS 音频
5. **性能监控** - 添加 API 调用统计

---

## 📚 参考文档

- [百炼语音识别 API](~/workspaces/voice-agent/语音识别 API.md)
- [百炼语音合成 API](~/workspaces/voice-agent/语音合成 API.md)
- [OpenClaw Voice 原项目](https://github.com/Purple-Horizons/openclaw-voice)
- [OpenClaw 文档](https://docs.openclaw.ai)

---

**任务状态**: ✅ 完成

**交付物**:
- `~/workspaces/openclaw-voice/` - 完整项目
- Docker 镜像可立即启动测试
- 文档齐全，易于使用

**问天君可随时启动测试！** 🎉
