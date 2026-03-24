# OpenClaw Voice - Claude Code 项目指南

## 项目概述

OpenClaw Voice 是一个实时语音对话后端服务，支持：
- 语音识别（STT）：Alibaba Bailian (Qwen-ASR)
- 大语言模型（LLM）：OpenAI 兼容 API
- 语音合成（TTS）：Alibaba Bailian (Qwen-TTS Realtime)
- WebSocket 实时通信

## 快速开始

```bash
# 安装依赖
./start.sh gateway start    # 启动 Gateway
./start.sh local start      # 启动本地 Voice Agent

# 访问
http://localhost:8765/     # V1 前端
http://localhost:8765/v2/    # V2 前端
```

## 项目结构

```
src/
├── server/
│   ├── main.py                    # WebSocket 入口，消息路由
│   ├── voice_turn.py             # 语音对话编排
│   ├── streaming_synthesis.py     # LLM+TTS 并行流
│   ├── turn_context.py            # 每次对话状态+取消
│   ├── message_router.py          # 消息处理函数
│   ├── connection.py             # WebSocket 连接封装，状态机
│   ├── audio.py                  # 音频缓冲
│   ├── messages.py                # 类型化消息解析
│   ├── tts/
│   │   ├── base.py               # TTSStream 基类
│   │   ├── bailian_tts.py        # HTTP SSE 实现
│   │   ├── bailian_tts_realtime.py  # WebSocket 真流实现
│   │   └── factory.py            # TTS 工厂
│   ├── stt/
│   │   ├── base.py               # STT 基类
│   │   ├── bailian_stt.py        # Bailian STT
│   │   └── factory.py            # STT 工厂
│   └── llm/
│       ├── base.py               # LLM 基类
│       ├── openai_llm.py         # OpenAI 兼容 LLM
│       └── factory.py            # LLM 工厂
└── client/                       # 前端静态文件
```

## 核心架构

### WebSocket 消息循环

```
websocket_endpoint
├── AudioBuffer              # 录音缓冲
├── ConnectionStateMachine   # 连接状态（IDLE/LISTENING/PROCESSING/SPEAKING）
├── TurnContext             # 每次对话状态+取消信号
├── VoiceTurn.execute()    # 完整对话流程
│   ├── STT  transcription
│   └── StreamingSynthesis.run()  # LLM+TTS 并行
│       ├── llm_feed_loop    # LLM token → TTS feed
│       └── tts_consume_loop  # TTS audio → WebSocket
└── Message handlers (message_router)
    ├── handle_start_listening
    ├── handle_stop_listening
    ├── handle_audio
    ├── handle_interrupt
    ├── handle_ping
    └── handle_perf_report
```

### TTS 流式接口

所有 TTS 实现必须继承 `BaseTTS` 并实现：

```python
class TTSStream:
    def feed(self, text: str) -> None: ...      # 喂入文本
    def finish(self) -> None: ...                 # 标记结束
    def __aiter__(self) -> AsyncGenerator[bytes]: ...  # yield 音频

class BaseTTS:
    def create_stream(self) -> TTSStream: ...
    async def close(self) -> None: ...
```

## 开发原则

### 1. 增量提交模式
每完成一个小改动就立即提交，不要等全部完成后再一次性提交。

### 2. Feature Branch
永远不在 main 分支上直接提交或修改代码。

### 3. 单一职责
每个模块/类只有一个清晰的职责：
- `StreamingSynthesis` - LLM+TTS 并行流
- `VoiceTurn` - 完整对话编排
- `message_router` - 消息处理

### 4. 开闭原则
对扩展开放，对修改关闭：
- 新增消息类型 → 在 `message_router.py` 添加 handler
- 新增 TTS provider → 实现 `BaseTTS` 接口

## 常用命令

```bash
# 运行测试
.venv/bin/python -m pytest tests/unit/test_main_websocket.py -v

# 启动服务
./start.sh local start

# 查看日志
tail -f .voice.log
```

## 配置

环境变量（`.env.local`）：
- `OPENCLAW_TTS_PROVIDER=bailian_realtime` - 使用实时 TTS
- `OPENCLAW_TTS_TIME_BUFFER_SECONDS=0.5` - TTS 缓冲时间
- `OPENCLAW_SUBTITLE_STREAMING=true` - 是否流式字幕
