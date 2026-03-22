# WebSocket Server 技能

## 概述

本技能指导如何理解和使用 voice-agent 项目的 WebSocket 服务器。

## 项目结构

```
src/server/
├── main.py                    # WebSocket 入口，消息路由
├── voice_turn.py             # VoiceTurn 类：完整对话编排
├── streaming_synthesis.py     # StreamingSynthesis 类：LLM+TTS 并行流
├── turn_context.py            # TurnContext：每次对话状态+取消
├── message_router.py         # 消息处理函数
├── connection.py            # WebSocketConnection, ConnectionStateMachine
├── audio.py                 # AudioBuffer
├── messages.py              # parse_message(), WSMessage 类型
└── tts/
    └── bailian_tts_realtime.py  # RealtimeTTSStream
```

## 架构概览

### WebSocket 消息循环

```
websocket_endpoint
├── AudioBuffer                 # 录音缓冲
├── ConnectionStateMachine      # 连接状态
├── TurnContext               # 对话状态+取消信号
├── VoiceTurn.execute()       # 完整对话流程
│   ├── STT transcription
│   └── StreamingSynthesis.run()
│       ├── llm_feed_loop     # LLM token → TTS feed
│       └── tts_consume_loop  # TTS audio → WebSocket
└── Message handlers (message_router.py)
    ├── handle_start_listening
    ├── handle_stop_listening
    ├── handle_audio
    ├── handle_interrupt
    ├── handle_ping
    └── handle_perf_report
```

### 状态机

```
IDLE -> LISTENING -> PROCESSING -> SPEAKING -> IDLE
                            ^              |
                            |______________|
```

## 核心实现

### 1. WebSocket 端点 (main.py)

```python
from .audio import AudioBuffer
from .connection import ConnectionStateMachine, ConnectionState
from .turn_context import TurnContext
from .voice_turn import VoiceTurn
from .messages import parse_message
from .message_router import (
    handle_start_listening,
    handle_stop_listening,
    handle_audio,
    handle_interrupt,
    handle_ping,
    handle_perf_report,
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # 初始化
    connection_state = ConnectionStateMachine()
    audio_buffer = AudioBuffer()
    turn_context = TurnContext()

    try:
        while True:
            raw = await websocket.receive_text()
            message = parse_message(raw)
            msg_type = message.type.value

            if msg_type == "start_listening":
                await handle_start_listening(
                    websocket=websocket,
                    connection_state=connection_state,
                    audio_buffer=audio_buffer,
                    cancel_callback=cancel_response,
                )
            elif msg_type == "stop_listening":
                new_task = await handle_stop_listening(...)
                if new_task:
                    response_task = new_task
            # ... 其他消息类型
    except WebSocketDisconnect:
        await cancel_response(send_interrupt_event=False)
```

### 2. VoiceTurn (voice_turn.py)

```python
class VoiceTurn:
    def __init__(self, stt, llm, tts, websocket, config, turn_context):
        self._stt = stt
        self._llm = llm
        self._tts = tts
        self._ws = websocket
        self._config = config
        self._turn_context = turn_context

    async def execute(self, audio_data: np.ndarray) -> str:
        # STT
        transcript, success = await self._stt.transcribe(audio_data)
        await self._ws.send_transcript(transcript)

        if not transcript.strip() or not success:
            await self._ws.send_listening_stopped()
            return ""

        # LLM + TTS
        self._state.transition_to(ConnectionState.SPEAKING)
        await self._ws.send_tts_start()

        synthesis = StreamingSynthesis(
            llm=self._llm,
            tts=self._tts,
            websocket=self._ws,
            config=self._config,
            turn_context=self._turn_context,
        )
        result = await synthesis.run(transcript)

        await self._ws.send_tts_end(interrupted=False)
        await self._ws.send_response_complete(result.full_response)
        await self._ws.send_listening_stopped()

        return result.full_response
```

### 3. StreamingSynthesis (streaming_synthesis.py)

```python
class StreamingSynthesis:
    async def run(self, transcript: str) -> SynthesisResult:
        tts_stream = self._tts.create_stream()

        async def llm_feed_loop():
            async for chunk in self._llm.chat_stream(transcript):
                full_response += chunk
                if self._config.subtitle_streaming:
                    await self._ws.send_subtitle_chunk(chunk)
                tts_stream.feed(chunk)
            tts_stream.finish()

        async def tts_consume_loop():
            tts_stream._ensure_connected()
            async for audio_chunk in tts_stream:
                if self._turn_context and self._turn_context.is_cancelled():
                    break
                buffer.extend(audio_chunk)
                # 缓冲后发送...

        await asyncio.gather(llm_feed_loop(), tts_consume_loop())
        return SynthesisResult(full_response=full_response, metrics=...)
```

## 消息协议

### 客户端 -> 服务器
| 消息类型 | 内容 | 说明 |
|---------|------|------|
| `start_listening` | `{}` | 开始录音 |
| `stop_listening` | `{}` | 停止录音 |
| `audio` | `{"data": base64}` | 音频数据 (float32) |
| `interrupt` | `{}` | 打断 AI 响应 |
| `ping` | `{}` | 心跳 |

### 服务器 -> 客户端
| 消息类型 | 内容 | 说明 |
|---------|------|------|
| `listening_started` | `{}` | 开始录音 |
| `listening_stopped` | `{}` | 停止录音 |
| `vad_status` | `{"speech_detected": bool}` | VAD 状态 |
| `transcript` | `{"text": str, "final": bool}` | 识别结果 |
| `subtitle_chunk` | `{"text": str}` | 实时字幕 |
| `tts_start` | `{}` | 开始播放 |
| `audio_chunk` | `{"data": base64, "sample_rate": int}` | 音频数据 |
| `tts_end` | `{"interrupted": bool}` | 播放结束 |
| `response_complete` | `{"text": str}` | 完整回复 |
| `interrupt_ack` | `{}` | 打断确认 |
| `pong` | `{}` | 心跳响应 |

## 消息处理函数 (message_router.py)

```python
async def handle_start_listening(websocket, connection_state, audio_buffer, cancel_callback):
    await cancel_callback(send_interrupt_event=False)
    audio_buffer.clear()
    connection_state.transition_to(ConnectionState.LISTENING)
    await websocket.send_json({"type": "listening_started"})

async def handle_stop_listening(websocket, connection_state, audio_buffer, turn_context, ...):
    if not connection_state.is_listening():
        await websocket.send_json({"type": "listening_stopped"})
        return None
    connection_state.transition_to(ConnectionState.PROCESSING)
    if audio_buffer.is_empty():
        await websocket.send_json({"type": "listening_stopped"})
        return None
    audio_data = audio_buffer.concatenate()
    audio_buffer.clear()
    turn_context.reset()
    # 创建 VoiceTurn 并返回 task

async def handle_audio(message, websocket, connection_state, audio_buffer, vad):
    if not connection_state.is_listening():
        return
    audio_np = np.frombuffer(message.audio_data, dtype=np.float32)
    audio_buffer.append(audio_np)
    if vad:
        has_speech = vad.is_speech(audio_np)
        await websocket.send_json({"type": "vad_status", "speech_detected": has_speech})

async def handle_interrupt(websocket, cancel_callback):
    await websocket.send_json({"type": "interrupt_ack"})
    await cancel_callback(send_interrupt_event=True)
```

## 取消机制

取消通过 `TurnContext` 和 `response_task` 两者实现：

```python
# TurnContext - 协作取消
class TurnContext:
    cancelled: asyncio.Event

    def cancel(self):
        self.cancelled.set()

    def is_cancelled(self) -> bool:
        return self.cancelled.is_set()

# cancel_response
async def cancel_response(send_interrupt_event: bool):
    turn_context.cancel()  # 协作取消
    if response_task and not response_task.done():
        response_task.cancel()
        try:
            await response_task
        except asyncio.CancelledError:
            pass
    if send_interrupt_event:
        await websocket.send_json({"type": "interrupt_complete"})
```

## 配置参数

```python
# TTS 流式配置
OPENCLAW_TTS_STREAMING: bool = True
OPENCLAW_SUBTITLE_STREAMING: bool = True
OPENCLAW_TTS_DATA_BUFFER_SIZE: int = 8192      # bytes
OPENCLAW_TTS_TIME_BUFFER_SECONDS: float = 0.5   # seconds
OPENCLAW_TTS_SAMPLE_RATE: int = 24000
OPENCLAW_TTS_PROVIDER: str = "bailian_realtime"
```

## 测试

```bash
# 运行 WebSocket 测试
.venv/bin/python -m pytest tests/unit/test_main_websocket.py -v

# 31 个测试全部通过
```
