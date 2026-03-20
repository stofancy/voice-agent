# WebSocket Server 技能

## 概述
本技能指导如何理解和使用 voice-agent 项目的 WebSocket 服务器。

## 项目结构
- 主服务器: `src/server/main.py` - FastAPI + WebSocket

## 架构概览

### 消息流程
```
客户端                    服务器
  |                        |
  |--- start_listening --->|
  |--- audio ( chunks )-->| (VAD 检测)
  |                        |
  |--- stop_listening ---->|
  |                        |--- transcribe (STT)
  |<-- transcript --------|
  |                        |--- chat_stream (LLM)
  |<-- subtitle_chunk -----|
  |                        |--- TTS stream
  |<-- tts_start ---------|
  |<-- audio_chunk (多次)-|
  |<-- tts_end -----------|
  |                        |
```

### 状态机
```
IDLE -> LISTENING -> PROCESSING -> SPEAKING -> IDLE
                            ^              |
                            |______________|
```

## 核心实现

### 1. WebSocket 端点
```python
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws")
@app.websocket("/voice/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # 处理连接
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            await handle_message(websocket, msg)
    except WebSocketDisconnect:
        # 客户端断开
        pass
```

### 2. 消息类型处理
```python
async def handle_message(websocket: WebSocket, msg: dict):
    msg_type = msg.get("type")

    if msg_type == "start_listening":
        # 开始录音
        await websocket.send_json({"type": "listening_started"})

    elif msg_type == "stop_listening":
        # 停止录音，处理音频
        audio_data = np.concatenate(audio_buffer)
        response_task = asyncio.create_task(run_turn(audio_data))

    elif msg_type == "audio":
        # 接收音频数据 (base64)
        audio_bytes = base64.b64decode(msg["data"])
        audio_np = np.frombuffer(audio_bytes, dtype=np.float32)
        audio_buffer.append(audio_np)

        # VAD 检测
        if vad:
            has_speech = vad.is_speech(audio_np)
            await websocket.send_json({
                "type": "vad_status",
                "speech_detected": has_speech,
            })

    elif msg_type == "interrupt":
        # 打断当前响应
        await cancel_response()
        await websocket.send_json({"type": "interrupt_ack"})

    elif msg_type == "ping":
        await websocket.send_json({"type": "pong"})
```

### 3. 处理流程 (run_turn)
```python
async def run_turn(audio_data: np.ndarray):
    # 1. STT - 语音转文字
    transcript, success = await stt.transcribe(audio_data)
    await websocket.send_json({
        "type": "transcript",
        "text": transcript,
        "final": True,
    })

    if not transcript.strip():
        await send_listening_stopped_once()
        return

    # 2. LLM - 对话生成
    full_response = ""
    tts_stream = tts.create_stream()

    async for chunk in backend.chat_stream(transcript):
        full_response += chunk
        # 实时字幕
        if SUBTITLE_STREAMING:
            await websocket.send_json({"type": "subtitle_chunk", "text": chunk})
        # 喂给 TTS
        tts_stream.feed(chunk)

    # 3. TTS - 语音合成
    tts_stream.finish()
    await websocket.send_json({"type": "tts_start"})

    # 发送音频块
    async for audio_chunk in tts_stream:
        buffer.extend(audio_chunk)
        # 缓冲后发送
        if len(buffer) >= TTS_DATA_BUFFER_SIZE:
            audio_b64 = base64.b64encode(bytes(buffer)).decode()
            await websocket.send_json({
                "type": "audio_chunk",
                "data": audio_b64,
                "sample_rate": TTS_SAMPLE_RATE,
            })
            buffer = bytearray()

    await websocket.send_json({"type": "tts_end", "interrupted": False})
    await send_listening_stopped_once()
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
| `response_chunk` | `{"text": str}` | 完整回复 (非流式) |
| `tts_start` | `{}` | 开始播放 |
| `audio_chunk` | `{"data": base64, "sample_rate": int}` | 音频数据 |
| `tts_end` | `{"interrupted": bool}` | 播放结束 |
| `interrupt_ack` | `{}` | 打断确认 |
| `pong` | `{}` | 心跳响应 |

## 认证和速率限制

### WebSocket 认证
```python
async def _validate_ws_auth(websocket: WebSocket):
    api_key_str = websocket.query_params.get("api_key") or \
                  websocket.headers.get("x-api-key")

    if settings.require_auth:
        if not api_key_str:
            await websocket.close(code=4001, reason="API key required")
            return None

        api_key = token_manager.validate_key(api_key_str)
        if not api_key:
            await websocket.close(code=4002, reason="Invalid API key")
            return None

        if not token_manager.check_rate_limit(api_key):
            await websocket.close(code=4003, reason="Rate limit exceeded")
            return None

    return api_key
```

### 错误码
- `4001`: API key required
- `4002`: Invalid API key
- `4003`: Rate limit exceeded

## 配置参数

```python
# 环境变量
OPENCLAW_HOST: str = "0.0.0.0"
OPENCLAW_PORT: int = 8765
OPENCLAW_REQUIRE_AUTH: bool = False

# TTS 流式配置
OPENCLAW_TTS_STREAMING: bool = True
OPENCLAW_SUBTITLE_STREAMING: bool = True
OPENCLAW_TTS_DATA_BUFFER_SIZE: int = 8192
OPENCLAW_TTS_TIME_BUFFER_SECONDS: float = 0.1
OPENCLAW_TTS_SAMPLE_RATE: int = 24000
```

## 性能优化

### 音频缓冲策略
```python
# 累积一定时间和数据量后发送
if (
    len(buffer) >= TTS_DATA_BUFFER_SIZE
    and time_buffer_elapsed >= TTS_TIME_BUFFER_SECONDS
):
    # 发送缓冲的音频
    buffer = bytearray()
    buffer_start_time = current_time
```

### 并发处理
```python
# 使用 asyncio.Task 处理响应
response_task = asyncio.create_task(run_turn(audio_data))

# 打断时取消任务
async def cancel_response():
    global response_task
    if response_task and not response_task.done():
        response_task.cancel()
        try:
            await response_task
        except asyncio.CancelledError:
            pass
    response_task = None
```
