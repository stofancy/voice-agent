"""TTS 工厂。根据 provider 自动选择实现。"""

from typing import TYPE_CHECKING, Optional

from loguru import logger

from .base import BaseTTS

if TYPE_CHECKING:
    from .bailian_tts import BailianTTS
    from .bailian_tts_realtime import BailianTTSRealtime


_PROVIDER_DEFAULTS = {
    "bailian": {
        "base_url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
        "model": "qwen3-tts-flash",
    },
    "bailian_realtime": {
        "base_url": "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
        "model": "qwen3-tts-flash-realtime",
    },
    "openai_compatible": {
        "base_url": "https://api.openai.com/v1",
        "model": "tts-1",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.0-flash",
    },
}


def create_tts(
    provider: str,
    api_key: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    voice: Optional[str] = None,
    language_type: str = "Chinese",
    instructions: Optional[str] = None,
    **kwargs,
) -> BaseTTS:
    if provider not in _PROVIDER_DEFAULTS:
        raise ValueError(
            f"Unknown TTS provider: {provider}. Available: {list(_PROVIDER_DEFAULTS.keys())}"
        )

    defaults = _PROVIDER_DEFAULTS[provider]
    resolved_base_url = base_url or defaults["base_url"]
    resolved_model = model or defaults["model"]

    if provider == "bailian":
        from .bailian_tts import BailianTTS

        logger.info(f"🔊 TTS factory: BailianTTS (url={resolved_base_url}, model={resolved_model})")
        tts: BaseTTS = BailianTTS(
            api_key=api_key,
            base_url=resolved_base_url,
            model=resolved_model,
            voice=voice,
            language_type=language_type,
            instructions=instructions,
            **kwargs,
        )
    elif provider == "bailian_realtime":
        from .bailian_tts_realtime import BailianTTSRealtime

        logger.info(
            f"🔊 TTS factory: BailianTTSRealtime (url={resolved_base_url}, model={resolved_model})"
        )
        tts = BailianTTSRealtime(
            api_key=api_key,
            base_url=resolved_base_url,
            model=resolved_model,
            voice=voice,
            language_type=language_type,
            instructions=instructions,
            **kwargs,
        )
    elif provider == "openai_compatible":
        from .openai_compatible_tts import OpenAICompatibleTTS

        logger.info(
            f"🔊 TTS factory: OpenAICompatibleTTS (url={resolved_base_url}, model={resolved_model})"
        )
        tts = OpenAICompatibleTTS(
            api_key=api_key,
            base_url=resolved_base_url,
            model=resolved_model,
            voice=voice,
            **kwargs,
        )
    elif provider == "gemini":
        from .gemini_tts import GeminiTTS

        logger.info(f"🔊 TTS factory: GeminiTTS (url={resolved_base_url}, model={resolved_model})")
        tts = GeminiTTS(
            api_key=api_key,
            base_url=resolved_base_url,
            model=resolved_model,
            voice=voice,
            **kwargs,
        )
    else:
        raise ValueError(f"TTS provider not implemented: {provider}")

    return tts
