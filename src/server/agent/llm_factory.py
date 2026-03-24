"""
LLM Factory for creating LangChain-compatible LLM instances.

Wraps the existing OpenAILLM or other backends for use with LangChain agents.
"""

from typing import Optional

from langchain_openai import ChatOpenAI

from ..llm.base import BaseLLM


class LangChainLLMWrapper:
    """
    Wrapper to adapt existing BaseLLM to LangChain compatible interface.

    This allows the existing Voice Agent LLM implementations to work
    with LangChain agents.
    """

    def __init__(
        self,
        llm: BaseLLM,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ):
        self._llm = llm
        self._model = model or llm.model_name
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def model(self) -> str:
        return self._model

    async def agenerate(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        """
        Generate response using the wrapped LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Generated text response
        """
        last_message = messages[-1]["content"] if messages else ""

        full_response = ""
        async for chunk in self._llm.chat_stream(last_message):
            full_response += chunk

        return full_response

    def as_langchain_llm(self) -> ChatOpenAI:
        """
        Get a LangChain-compatible ChatOpenAI instance.

        Note: This creates a new ChatOpenAI instance that shares
        the same API configuration as the wrapped LLM.
        """
        return ChatOpenAI(
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            api_key=self._llm.api_key,
            base_url=self._llm.url,
        )


def create_langchain_llm(
    llm: BaseLLM,
    model: Optional[str] = None,
    temperature: float = 0.7,
) -> LangChainLLMWrapper:
    """
    Create a LangChain-compatible LLM wrapper.

    Args:
        llm: Existing BaseLLM implementation
        model: Optional model name override
        temperature: Sampling temperature

    Returns:
        LangChainLLMWrapper instance
    """
    return LangChainLLMWrapper(
        llm=llm,
        model=model,
        temperature=temperature,
    )
