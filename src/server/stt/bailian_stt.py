"""
百炼 STT — HTTP 实现。

通过 DashScope OpenAI 兼容 API 识别语音。
"""

import asyncio
import base64
import io
import os
import wave
from typing import Optional, Tuple

import numpy as np
from loguru import logger

from .base import BaseSTT


class BailianSTT(BaseSTT):
    """百炼语音识别（Qwen-ASR）"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        language: str = "zh",
        **kwargs,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.language = language
        self._client = None
        self._setup_client()

    def _setup_client(self):
        try:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info(f"✅ BailianSTT ready (url={self.base_url}, model={self.model})")
        except ImportError:
            logger.error("❌ openai package not installed")
            self._client = None

    async def transcribe(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
    ) -> Tuple[str, bool]:
        if self._client is None:
            raise RuntimeError("STT not initialized")

        try:
            # 重采样到 16kHz
            if sample_rate != 16000:
                try:
                    from scipy import signal

                    num_samples = int(len(audio_data) * 16000 / sample_rate)
                    audio_data = signal.resample(audio_data, num_samples)
                except ImportError:
                    ratio = 16000 / sample_rate
                    audio_data = (
                        audio_data[:: int(1 / ratio)]
                        if ratio < 1
                        else np.repeat(audio_data, int(ratio))
                    )
                sample_rate = 16000

            wav_data = self._numpy_to_wav(audio_data, sample_rate)
            base64_audio = base64.b64encode(wav_data).decode("utf-8")
            data_uri = f"data:audio/wav;base64,{base64_audio}"

            logger.debug(
                f"📤 STT request: {len(audio_data)} samples, {len(audio_data) / 16000:.2f}s"
            )

            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [{"type": "input_audio", "input_audio": {"data": data_uri}}],
                    }
                ],
                extra_body={
                    "asr_options": {
                        "language": self.language,
                        "enable_itn": True,
                    }
                },
            )

            text = response.choices[0].message.content
            logger.info(f"🎤 STT result: {text}")
            return text, True

        except Exception as e:
            logger.error(f"❌ STT error: {type(e).__name__}: {e}")
            return f"识别失败：{str(e)}", False

    def _numpy_to_wav(self, audio_data: np.ndarray, sample_rate: int) -> bytes:
        if audio_data.dtype in (np.float32, np.float64):
            audio_int16 = (audio_data * 32767).astype(np.int16)
        else:
            audio_int16 = audio_data.astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        return buffer.getvalue()

    async def close(self) -> None:
        self._client = None
