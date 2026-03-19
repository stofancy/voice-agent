"""
TTS 工厂。

根据 model 名称自动选择 TTS 实现。
main.py 只调用此工厂，不直接 import 具体实现。
"""

from typing import Optional
from loguru import logger
from .tts_base import BaseTTS


def create_tts(
    api_key: str,
    model: str,
    voice: str,
    language_type: str = "Chinese",
    instructions: Optional[str] = None,
    **kwargs,
) -> BaseTTS:
    """
    根据 model 名称创建对应的 TTS 实例。

    - model 含 "realtime" → BailianTTSRealtime (WebSocket 双工)
    - 其他 → BailianTTS (HTTP SSE)
    """
    if "realtime" in model:
        from .bailian_tts_realtime import BailianTTSRealtime

        logger.info(f"🔊 TTS 工厂: 创建 BailianTTSRealtime (model={model}, voice={voice})")
        return BailianTTSRealtime(
            api_key=api_key,
            model=model,
            voice=voice,
            language_type=language_type,
            instructions=instructions,
            **kwargs,
        )
    else:
        from .bailian_tts_adapter import BailianTTSAdapter

        logger.info(f"🔊 TTS 工厂: 创建 BailianTTSAdapter (model={model}, voice={voice})")
        return BailianTTSAdapter(
            api_key=api_key,
            model=model,
            voice=voice,
            language_type=language_type,
            instructions=instructions,
            **kwargs,
        )
