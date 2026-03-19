"""TTS 工厂。根据 model 名称自动选择实现。"""

from typing import Optional
from loguru import logger
from .base import BaseTTS


def create_tts(
    api_key: str,
    model: str,
    voice: str,
    language_type: str = "Chinese",
    instructions: Optional[str] = None,
    **kwargs,
) -> BaseTTS:
    if "realtime" in model:
        from .bailian_tts_realtime import BailianTTSRealtime

        logger.info(f"🔊 TTS factory: BailianTTSRealtime (model={model}, voice={voice})")
        return BailianTTSRealtime(
            api_key=api_key, model=model, voice=voice,
            language_type=language_type, instructions=instructions, **kwargs,
        )
    else:
        from .bailian_tts import BailianTTS

        logger.info(f"🔊 TTS factory: BailianTTS (model={model}, voice={voice})")
        return BailianTTS(
            api_key=api_key, model=model, voice=voice,
            language_type=language_type, instructions=instructions, **kwargs,
        )
