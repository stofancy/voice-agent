"""OpenAI-compatible STT via /audio/transcriptions endpoint."""

from typing import Optional, Tuple

import numpy as np
from loguru import logger

from .base import BaseSTT


class OpenAICompatibleSTT(BaseSTT):
    """OpenAI-compatible Speech-to-Text (e.g. Groq, Together, etc.)"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        language: str = "en",
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

            self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info(f"✅ OpenAICompatibleSTT ready (url={self.base_url}, model={self.model})")
        except ImportError:
            logger.error("❌ openai package not installed")
            self._client = None

    async def transcribe(
        self, audio_data: np.ndarray, sample_rate: int = 16000
    ) -> Tuple[str, bool]:
        raise NotImplementedError("OpenAI-compatible STT not yet implemented")

    async def close(self) -> None:
        self._client = None
