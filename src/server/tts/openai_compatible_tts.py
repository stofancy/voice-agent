"""OpenAI-compatible TTS."""

from typing import Optional

from loguru import logger

from .base import BaseTTS, TTSStream


class OpenAICompatibleTTS(BaseTTS):
    """OpenAI-compatible Text-to-Speech"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        voice: Optional[str] = None,
        **kwargs,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.voice = voice or "alloy"
        logger.info(
            f"✅ OpenAICompatibleTTS ready (url={self.base_url}, model={self.model}, voice={self.voice})"
        )

    def create_stream(self) -> TTSStream:
        raise NotImplementedError("OpenAI-compatible TTS not yet implemented")

    async def close(self) -> None:
        pass
