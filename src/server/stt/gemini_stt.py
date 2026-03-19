"""Gemini STT."""

from typing import Tuple

import numpy as np
from loguru import logger

from .base import BaseSTT


class GeminiSTT(BaseSTT):
    """Gemini speech-to-text"""

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
        logger.info(f"✅ GeminiSTT ready (url={self.base_url}, model={self.model})")

    async def transcribe(
        self, audio_data: np.ndarray, sample_rate: int = 16000
    ) -> Tuple[str, bool]:
        raise NotImplementedError("Gemini STT not yet implemented")

    async def close(self) -> None:
        pass
