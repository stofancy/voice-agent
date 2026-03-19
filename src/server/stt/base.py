"""STT 抽象接口定义。"""

from abc import ABC, abstractmethod
from typing import Tuple

import numpy as np


class BaseSTT(ABC):
    """
    STT 引擎抽象基类。

    所有 STT 实现必须继承此类并实现 transcribe() 和 close()。
    """

    @abstractmethod
    async def transcribe(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
    ) -> Tuple[str, bool]:
        """
        识别音频。

        Args:
            audio_data: PCM 音频 (numpy float32)
            sample_rate: 采样率

        Returns:
            (识别文本, 是否成功)
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """释放资源"""
        ...
