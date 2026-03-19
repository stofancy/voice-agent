"""
百炼 TTS — HTTP SSE 实现。

通过 DashScope HTTP API 合成语音，支持流式音频输出。
文本输入为一次性（非流式），feed() 攒文本，finish() 后一次性合成。
"""

import asyncio
import base64
import json
import os
from typing import AsyncGenerator, Optional

import aiohttp
from loguru import logger

from .base import BaseTTS, TTSStream


class BailianTTS(BaseTTS):
    """百炼语音合成（Qwen-TTS）— HTTP SSE"""

    AVAILABLE_VOICES = {
        "Cherry": "甜美女性",
        "Bella": "温柔女性",
        "Sarah": "成熟女性",
        "Jack": "沉稳男性",
        "Allie": "活泼女性",
    }

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
        self.api_key = api_key
        self.model = model
        self.voice = voice or "Cherry"
        self.language_type = language_type
        self.instructions = instructions
        self.api_url = base_url
        self._session: Optional[aiohttp.ClientSession] = None

        instruct_info = f", instructions: {self.instructions[:30]}..." if self.instructions else ""
        logger.info(f"✅ BailianTTS ready (model={self.model}, voice={self.voice}{instruct_info})")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def create_stream(self) -> TTSStream:
        return _BufferedStream(self)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _synthesize(self, text: str) -> AsyncGenerator[bytes, None]:
        """合成语音，流式返回 PCM 音频块"""
        session = await self._get_session()

        input_data = {
            "text": text,
            "voice": self.voice,
            "language_type": self.language_type,
        }
        if self.instructions:
            input_data["instructions"] = self.instructions
            input_data["optimize_instructions"] = True

        payload = {"model": self.model, "input": input_data}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable",
        }

        logger.debug(f"🔊 TTS request: {text[:50]}...")

        async with session.post(self.api_url, json=payload, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"❌ TTS API error: {response.status} - {error_text}")
                return

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


class _BufferedStream(TTSStream):
    """攒完所有文本再一次性合成"""

    def __init__(self, tts: BailianTTS):
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
        async for chunk in self._tts._synthesize(self._buffer):
            yield chunk
