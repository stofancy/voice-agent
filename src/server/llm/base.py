"""LLM 抽象接口定义。"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseLLM(ABC):
    """
    LLM 引擎抽象基类。

    所有 LLM 实现必须继承此类。
    """

    @abstractmethod
    async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        """
        流式对话。

        Args:
            user_message: 用户消息

        Yields:
            文本 chunk
        """
        ...

    @abstractmethod
    def clear_history(self) -> None:
        """清除对话历史"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """释放资源"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """当前模型名"""
        ...
