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
        "Maia": "四月音色，知性与温柔",
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
        return _IncrementalStream(self)

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


class _IncrementalStream(TTSStream):
    """
    增量 TTS 流：feed() 时边接收文本边合成音频。

    内部启动后台任务，当累积文本达到 min_text_length 时自动触发合成。
    """

    def __init__(self, tts: BailianTTS, min_text_length: int = 10):
        self._tts = tts
        self._min_text_length = min_text_length
        self._buffer = ""
        self._finished = False
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._synth_task: Optional[asyncio.Task] = None

    def feed(self, text: str) -> None:
        self._buffer += text
        # 启动后台合成任务（如果还没启动）
        if self._synth_task is None or self._synth_task.done():
            self._synth_task = asyncio.create_task(self._synthesize_loop())

    def finish(self) -> None:
        self._finished = True
        # 通知合成任务结束
        if self._synth_task and not self._synth_task.done():
            self._synth_task.cancel()

    async def _synthesize_loop(self) -> None:
        """后台任务：累积文本，达到阈值时合成"""
        while not self._finished or self._buffer:
            if len(self._buffer) >= self._min_text_length:
                text_to_synth = self._buffer
                self._buffer = ""
                try:
                    async for chunk in self._tts._synthesize(text_to_synth):
                        await self._audio_queue.put(chunk)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"❌ Incremental TTS error: {e}")
                    break
            else:
                await asyncio.sleep(0.05)  # 等待更多文本

        # 发送剩余文本的音频
        if self._buffer:
            text_to_synth = self._buffer
            self._buffer = ""
            try:
                async for chunk in self._tts._synthesize(text_to_synth):
                    await self._audio_queue.put(chunk)
            except Exception as e:
                logger.error(f"❌ Final TTS error: {e}")

        await self._audio_queue.put(b"__END__")

    async def __aiter__(self) -> AsyncGenerator[bytes, None]:
        while True:
            chunk = await self._audio_queue.get()
            if chunk == b"__END__":
                break
            yield chunk
