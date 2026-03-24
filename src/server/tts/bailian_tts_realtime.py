"""
BailianTTSRealtime — QwenTtsRealtime WebSocket 双工 TTS。

支持流式文本输入 + 流式音频输出，使用 server_commit 模式。
LLM 每产出一个 token 就 feed() 给 TTS，TTS 自行决定何时开始合成。
"""

import asyncio
import base64
from typing import AsyncGenerator, Optional

from dashscope.audio.qwen_tts_realtime import (
    AudioFormat,
    QwenTtsRealtime,
    QwenTtsRealtimeCallback,
)
from loguru import logger

from .base import BaseTTS, TTSStream


class RealtimeTTSStream(TTSStream):
    """
    真流式 TTS 会话。

    - feed(text) → QwenTtsRealtime.append_text(text)
    - finish()   → QwenTtsRealtime.finish()
    - __aiter__  → 从 callback queue 取音频 yield
    """

    def __init__(
        self,
        model: str,
        voice: str,
        api_key: str,
        base_url: str,
        language_type: str = "Chinese",
        instructions: Optional[str] = None,
    ):
        self._model = model
        self._voice = voice
        self._api_key = api_key
        self._language_type = language_type
        self._instructions = instructions
        self._base_url = base_url

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._queue: Optional[asyncio.Queue] = None
        self._tts: Optional[QwenTtsRealtime] = None
        self._connected = False
        self._first_audio = True

    def _ensure_connected(self) -> None:
        """懒连接：第一次 feed() 时建立 WebSocket"""
        if self._connected:
            return

        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()

        callback = _StreamCallback(self._queue, self._loop)
        self._tts = QwenTtsRealtime(
            model=self._model,
            callback=callback,
            url=self._base_url,
        )
        # Override instance-level api key instead of setting global dashscope.api_key
        # to avoid race condition with concurrent streams
        self._tts.apikey = self._api_key
        self._tts.connect()

        # 配置 session
        # SDK type hints are incomplete for update_session, using direct params
        self._tts.update_session(
            voice=self._voice,
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            mode="server_commit",
            **(
                {"instructions": self._instructions, "optimize_instructions": True}
                if self._instructions
                else {}
            ),
        )
        self._connected = True
        logger.debug(f"🔊 RealtimeTTSStream connected: model={self._model}, voice={self._voice}")

    def feed(self, text: str) -> None:
        self._ensure_connected()
        tts = self._tts
        if text and tts is not None:
            tts.append_text(text)

    def finish(self) -> None:
        if self._tts and self._connected:
            self._tts.finish()

    async def __aiter__(self) -> AsyncGenerator[bytes, None]:
        if self._queue is None:
            return

        while True:
            item = await self._queue.get()
            if item is None:
                # 哨兵：session 结束
                break
            yield item


class _StreamCallback(QwenTtsRealtimeCallback):
    """
    QwenTtsRealtime 的回调，将音频数据桥接到 asyncio.Queue。
    注意：on_event 在 websocket 线程中调用，需要 thread-safe 地写入 asyncio Queue。
    """

    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self._queue = queue
        self._loop = loop

    def on_open(self) -> None:
        logger.debug("🔊 TTS Realtime WebSocket opened")

    def on_close(self, close_status_code, close_msg) -> None:
        logger.debug(f"🔊 TTS Realtime WebSocket closed: code={close_status_code}, msg={close_msg}")
        # 确保迭代器能退出
        self._loop.call_soon_threadsafe(self._queue.put_nowait, None)

    def on_event(self, message: dict) -> None:  # type: ignore
        try:
            etype = message.get("type", "")

            if etype == "response.audio.delta":
                audio_bytes = base64.b64decode(message["delta"])
                self._loop.call_soon_threadsafe(self._queue.put_nowait, audio_bytes)

            elif etype == "session.finished":
                logger.debug("🔊 TTS Realtime session finished")
                self._loop.call_soon_threadsafe(self._queue.put_nowait, None)

            elif etype == "error":
                error_info = message.get("error", {})
                logger.error(f"🔊 TTS Realtime error: {error_info}")
                self._loop.call_soon_threadsafe(self._queue.put_nowait, None)

        except Exception as e:
            logger.error(f"🔊 TTS Realtime callback error: {e}")
            self._loop.call_soon_threadsafe(self._queue.put_nowait, None)


class BailianTTSRealtime(BaseTTS):
    """
    QwenTtsRealtime 的 BaseTTS 实现。

    每次 create_stream() 创建一个新的 WebSocket 会话。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        voice: Optional[str] = None,
        language_type: str = "Chinese",
        instructions: Optional[str] = None,
        **kwargs,
    ):
        self._api_key = api_key
        self._model = model
        self._voice = voice or "Cherry"
        self._language_type = language_type
        self._instructions = instructions
        self._base_url = base_url

        instruct_info = (
            f", instructions: {self._instructions[:30]}..." if self._instructions else ""
        )
        logger.info(
            f"✅ BailianTTSRealtime ready (model={self._model}, voice={self._voice}{instruct_info})"
        )

    def create_stream(self) -> TTSStream:
        return RealtimeTTSStream(
            model=self._model,
            voice=self._voice,
            api_key=self._api_key,
            base_url=self._base_url,
            language_type=self._language_type,
            instructions=self._instructions,
        )

    async def close(self) -> None:
        pass  # 每个 stream 自行管理连接生命周期
