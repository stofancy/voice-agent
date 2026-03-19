"""STT 工厂。根据 model 名称自动选择实现。"""

from typing import Optional
from loguru import logger
from .base import BaseSTT


def create_stt(
    api_key: str,
    model: str,
    language: str = "zh",
    **kwargs,
) -> BaseSTT:
    # 目前只有百炼，后续可按 model 名扩展
    from .bailian_stt import BailianSTT

    logger.info(f"🎤 STT factory: BailianSTT (model={model})")
    return BailianSTT(api_key=api_key, model=model, language=language, **kwargs)
