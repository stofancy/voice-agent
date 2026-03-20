# TTS Provider 技能

## 概述
本技能指导如何为 voice-agent 项目实现 Text-to-Speech (TTS) 语音合成 provider。

## 项目结构
- 基础抽象类: `src/server/tts/base.py` - `BaseTTS`, `TTSStream`
- 工厂模式: `src/server/tts/factory.py` - `create_tts()`
- 具体实现: `src/server/tts/*.py`

## 核心概念

### TTSStream
`TTSStream` 是流式音频会话的抽象，main.py 使用模式:

```python
tts_stream = tts.create_stream()

# LLM 每个 chunk 产出时调用 feed()
async for chunk in backend.chat_stream(transcript):
    tts_stream.feed(chunk)

# 文本输入完成后调用 finish()
tts_stream.finish()

# 异步迭代获取音频块
async for audio_chunk in tts_stream:
    send_to_client(audio_chunk)
```

## 如何实现新的 TTS Provider

### 1. 创建 TTSStream 实现类
继承 `TTSStream` 抽象类:

```python
from .base import TTSStream
from typing import AsyncGenerator

class MyTTSStream(TTSStream):
    def __init__(self, tts: "MyTTS"):
        self._tts = tts
        self._buffer = ""
        self._finished = False

    def feed(self, text: str) -> None:
        """累积文本"""
        self._buffer += text

    def finish(self) -> None:
        """标记文本输入结束"""
        self._finished = True

    async def __aiter__(self) -> AsyncGenerator[bytes, None]:
        """异步迭代，返回 PCM 音频块"""
        if not self._buffer.strip():
            return
        # 调用 TTS 合成并 yield 音频块
        async for chunk in self._tts._synthesize(self._buffer):
            yield chunk
```

### 2. 创建 BaseTTS 实现类
继承 `BaseTTS` 抽象类:

```python
from .base import BaseTTS, TTSStream
from typing import Optional, AsyncGenerator
import aiohttp
import base64
import json

class MyTTS(BaseTTS):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        voice: Optional[str] = None,
        language_type: str = "Chinese",
        instructions: Optional[str] = None,
        **kwargs
    ):
        self.api_key = api_key
        self.model = model
        self.voice = voice or "default_voice"
        self.language_type = language_type
        self.instructions = instructions
        self.api_url = base_url
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def create_stream(self) -> TTSStream:
        """创建流式会话"""
        return MyTTSStream(self)

    async def _synthesize(self, text: str) -> AsyncGenerator[bytes, None]:
        """合成语音，返回 PCM 音频块"""
        session = await self._get_session()

        payload = {
            "model": self.model,
            "input": {
                "text": text,
                "voice": self.voice,
                "language_type": self.language_type,
            }
        }
        if self.instructions:
            payload["input"]["instructions"] = self.instructions

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with session.post(self.api_url, json=payload, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                return

            # 解析 SSE 流
            async for line in response.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data and data != "[DONE]":
                        try:
                            chunk = json.loads(data)
                            audio_data = chunk.get("output", {}).get("audio", {}).get("data", "")
                            if audio_data:
                                yield base64.b64decode(audio_data)
                        except json.JSONDecodeError:
                            continue

    async def close(self) -> None:
        """释放资源"""
        if self._session and not self._session.closed:
            await self._session.close()
```

### 3. 注册到工厂
在 `src/server/tts/factory.py` 中添加:

```python
# 添加 provider 默认配置
_PROVIDER_DEFAULTS = {
    # ... 其他 providers
    "my_provider": {
        "base_url": "https://api.example.com/v1/tts",
        "model": "my-tts-model",
    },
}

# 在 create_tts() 函数中添加分支
elif provider == "my_provider":
    from .my_tts import MyTTS
    tts = MyTTS(
        api_key=api_key,
        base_url=resolved_base_url,
        model=resolved_model,
        voice=voice,
        language_type=language_type,
        instructions=instructions,
        **kwargs,
    )
```

## 流式模式

### HTTP SSE 流式
适用于非实时场景，文本累积后一次性合成:

```python
class _BufferedStream(TTSStream):
    def __init__(self, tts: MyTTS):
        self._tts = tts
        self._buffer = ""
        self._finished = False

    def feed(self, text: str) -> None:
        self._buffer += text

    def finish(self) -> None:
        self._finished = True

    async def __aiter__(self) -> AsyncGenerator[bytes, None]:
        if not self._buffer.strip():
            return
        # 一次性合成全部文本
        async for chunk in self._tts._synthesize(self._buffer):
            yield chunk
```

### WebSocket 实时流式
适用于实时语音场景，实时合成实时返回:

```python
import websockets
import json
import asyncio

class RealtimeTTSStream(TTSStream):
    def __init__(self, tts: "RealtimeTTS"):
        self._tts = tts
        self._ws = None
        self._queue = asyncio.Queue()

    def feed(self, text: str) -> None:
        # 实时发送到 WebSocket
        asyncio.create_task(self._ws.send(json.dumps({
            "type": "input_text",
            "text": text
        })))

    def finish(self) -> None:
        asyncio.create_task(self._ws.send(json.dumps({"type": "done"})))

    async def __aiter__(self) -> AsyncGenerator[bytes, None]:
        while True:
            chunk = await self._queue.get()
            if chunk is None:  # 结束信号
                break
            yield chunk
```

## 现有 TTS Providers
- `bailian`: 阿里云百炼 Qwen-TTS (HTTP SSE)
- `bailian_realtime`: 阿里云百炼 Qwen-TTS (WebSocket 实时)
- `openai_compatible`: OpenAI TTS 兼容 API
- `gemini`: Google Gemini TTS

## 可用音色 (Bailian)
```python
AVAILABLE_VOICES = {
    "Cherry": "甜美女性",
    "Bella": "温柔女性",
    "Sarah": "成熟女性",
    "Jack": "沉稳男性",
    "Allie": "活泼女性",
    "Maia": "四月音色，知性与温柔",
}
```

## 环境配置
通过环境变量配置:
- `OPENCLAW_TTS_PROVIDER`: provider 名称
- `OPENCLAW_TTS_API_KEY`: API 密钥
- `OPENCLAW_TTS_MODEL`: 模型名称
- `OPENCLAW_TTS_VOICE`: 音色名称
- `OPENCLAW_TTS_BASE_URL`: API 地址
- `OPENCLAW_TTS_LANGUAGE`: 语言类型 (默认 "Chinese")
- `OPENCLAW_TTS_INSTRUCTIONS`: 自定义指令

## 音频输出配置
- `OPENCLAW_TTS_STREAMING`: 是否启用流式 (默认 true)
- `OPENCLAW_TTS_DATA_BUFFER_SIZE`: 缓冲区大小 (默认 8192)
- `OPENCLAW_TTS_TIME_BUFFER_SECONDS`: 时间缓冲秒数 (默认 0.1)
- `OPENCLAW_TTS_SAMPLE_RATE`: 采样率 (默认 24000)
