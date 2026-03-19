"""LLM 工厂。根据 provider 自动选择实现。"""

import os
from typing import TYPE_CHECKING, Optional

from loguru import logger

from .base import BaseLLM

if TYPE_CHECKING:
    from .openai_llm import OpenAILLM
    from .gemini_llm import GeminiLLM


# Pre-defined tuple for OpenAI-compatible providers (avoid tuple recreation per call)
_OPENAI_COMPATIBLE_PROVIDERS = ("openclaw_gateway", "bailian", "openai")

_PROVIDER_DEFAULTS = {
    "openclaw_gateway": {
        "base_url": "https://dashscope.aliyuncs.com/api-ws/v1/realtime",
        "model": "openclaw:main",
    },
    "bailian": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3.5-flash",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.0-flash",
    },
}


def create_llm(
    provider: str,
    api_key: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    **kwargs,
) -> BaseLLM:
    if provider not in _PROVIDER_DEFAULTS:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Available: {list(_PROVIDER_DEFAULTS.keys())}"
        )

    defaults = _PROVIDER_DEFAULTS[provider]
    resolved_base_url = base_url or defaults["base_url"]
    resolved_model = model or defaults["model"]

    if provider in _OPENAI_COMPATIBLE_PROVIDERS:
        from .openai_llm import OpenAILLM

        logger.info(f"🤖 LLM factory: OpenAILLM (provider={provider}, url={resolved_base_url}, model={resolved_model})")
        llm: BaseLLM = OpenAILLM(
            url=resolved_base_url,
            model=resolved_model,
            api_key=api_key,
            system_prompt=system_prompt,
            **kwargs,
        )
    elif provider == "gemini":
        from .gemini_llm import GeminiLLM

        logger.info(f"🤖 LLM factory: GeminiLLM (url={resolved_base_url}, model={resolved_model})")
        llm = GeminiLLM(
            base_url=resolved_base_url,
            model=resolved_model,
            api_key=api_key,
            system_prompt=system_prompt,
            **kwargs,
        )
    else:
        # This should never be reached due to earlier validation
        raise ValueError(f"LLM provider not implemented: {provider}")

    return llm
