"""
BailianTTS 适配器 — 将现有 BailianTTS 包装为 BaseTTS 接口。

不修改 bailian_tts.py 任何代码，只做接口适配。
内部实现：feed() 攒文本，finish() 后一次性调用 synthesize()。
"""

import asyncio
from typing import AsyncGenerator, Optional

from loguru import logger

from .tts_base import BaseTTS, TTSStream
from .bailian_tts import BailianTTS


class BufferedTTSStream(TTSStream):
    """
    缓冲式 TTS 流：攒完所有文本再一次性合成。
    用于包装不支持流式文本输入的 TTS 实现。
    """

    def __init__(self, tts: BailianTTS, stream: bool = True):
        self._tts = tts
        self._stream = stream
        self._buffer = ""
        self._finished = False

    def feed(self, text: str) -> None:
        self._buffer += text

    def finish(self) -> None:
        self._finished = True

    async def __aiter__(self) -> AsyncGenerator[bytes, None]:
        if not self._finished:
            logger.warning("TTSStream: iterating before finish() called, proceeding anyway")

        if not self._buffer.strip():
            return

        async for chunk in self._tts.synthesize(self._buffer, stream=self._stream):
            yield chunk


class BailianTTSAdapter(BaseTTS):
    """
    将现有 BailianTTS 适配为 BaseTTS 接口。
    bailian_tts.py 零改动。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen3-tts-flash",
        voice: str = "Cherry",
        language_type: str = "Chinese",
        instructions: Optional[str] = None,
        **kwargs,
    ):
        self._tts = BailianTTS(
            api_key=api_key,
            model=model,
            voice=voice,
            language_type=language_type,
            instructions=instructions,
        )

    def create_stream(self) -> TTSStream:
        return BufferedTTSStream(self._tts, stream=True)

    async def close(self) -> None:
        await self._tts.close()
