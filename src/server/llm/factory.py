"""LLM 工厂。根据配置自动选择实现。"""

from typing import Optional
from loguru import logger
from .base import BaseLLM


def create_llm(
    url: str,
    model: str,
    api_key: Optional[str] = None,
    system_prompt: Optional[str] = None,
    **kwargs,
) -> BaseLLM:
    # 目前统一用 OpenAI 兼容接口（含 OpenClaw Gateway）
    from .openai_llm import OpenAILLM

    logger.info(f"🤖 LLM factory: OpenAILLM (url={url}, model={model})")
    return OpenAILLM(
        url=url, model=model, api_key=api_key,
        system_prompt=system_prompt, **kwargs,
    )
