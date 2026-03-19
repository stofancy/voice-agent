"""STT 工厂。根据 provider 自动选择实现。"""

from typing import TYPE_CHECKING, Optional

from loguru import logger

from .base import BaseSTT

if TYPE_CHECKING:
    from .bailian_stt import BailianSTT


_PROVIDER_DEFAULTS = {
    "bailian": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3-asr-flash",
    },
    "openai_compatible": {
        "base_url": "https://api.openai.com/v1",
        "model": "whisper-1",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.0-flash",
    },
}


def create_stt(
    provider: str,
    api_key: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    language: str = "zh",
    **kwargs,
) -> BaseSTT:
    if provider not in _PROVIDER_DEFAULTS:
        raise ValueError(
            f"Unknown STT provider: {provider}. Available: {list(_PROVIDER_DEFAULTS.keys())}"
        )

    defaults = _PROVIDER_DEFAULTS[provider]
    resolved_base_url = base_url or defaults["base_url"]
    resolved_model = model or defaults["model"]

    if provider == "bailian":
        from .bailian_stt import BailianSTT

        logger.info(f"🎤 STT factory: BailianSTT (url={resolved_base_url}, model={resolved_model})")
        stt: BaseSTT = BailianSTT(
            api_key=api_key,
            base_url=resolved_base_url,
            model=resolved_model,
            language=language,
            **kwargs,
        )
    elif provider == "openai_compatible":
        from .openai_compatible_stt import OpenAICompatibleSTT

        logger.info(
            f"🎤 STT factory: OpenAICompatibleSTT (url={resolved_base_url}, model={resolved_model})"
        )
        stt = OpenAICompatibleSTT(
            api_key=api_key,
            base_url=resolved_base_url,
            model=resolved_model,
            language=language,
            **kwargs,
        )
    elif provider == "gemini":
        from .gemini_stt import GeminiSTT

        logger.info(f"🎤 STT factory: GeminiSTT (url={resolved_base_url}, model={resolved_model})")
        stt = GeminiSTT(
            api_key=api_key,
            base_url=resolved_base_url,
            model=resolved_model,
            language=language,
            **kwargs,
        )
    else:
        raise ValueError(f"STT provider not implemented: {provider}")

    return stt
