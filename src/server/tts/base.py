"""
TTS 抽象接口定义。

所有 TTS 实现必须继承 BaseTTS 并实现 create_stream()。
main.py 只依赖这两个抽象类，不依赖任何具体实现。
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class TTSStream(ABC):
    """
    一次对话的 TTS 流式会话。

    用法:
        stream = tts.create_stream()
        stream.feed("你好")      # LLM 每个 chunk 调一次
        stream.feed("世界")
        stream.finish()           # 标记文本输入结束
        async for audio in stream:  # 异步迭代获取音频块
            send_to_client(audio)
    """

    def _ensure_connected(self) -> None:
        """
        懒连接：确保 TTS 连接已建立。

        对于需要提前建立连接的 TTS 实现（如 WebSocket），
        可覆盖此方法。否则默认空实现（HTTP SSE 等按需连接）。
        """
        pass

    @abstractmethod
    def feed(self, text: str) -> None:
        """喂入一段文本（LLM 每产出一个 chunk 调用一次）"""
        ...

    @abstractmethod
    def finish(self) -> None:
        """标记文本输入结束，通知 TTS 可以结束合成"""
        ...

    @abstractmethod
    def __aiter__(self) -> AsyncGenerator[bytes, None]:
        """异步迭代，yield PCM 音频数据块"""
        ...


class BaseTTS(ABC):
    """
    TTS 引擎抽象基类。

    所有 TTS 实现（BailianTTS, BailianTTSRealtime, EdgeTTS, ...）
    必须继承此类并实现 create_stream() 和 close()。
    """

    @abstractmethod
    def create_stream(self) -> TTSStream:
        """创建一个新的流式 TTS 会话"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """释放资源（HTTP session, WebSocket 连接等）"""
        ...
