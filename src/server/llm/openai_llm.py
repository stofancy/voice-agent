"""
OpenAI 兼容 LLM — 支持 OpenClaw Gateway 和直连 OpenAI API。
"""

import os
from typing import AsyncGenerator, Dict, List, Optional

import httpx
from loguru import logger

from .base import BaseLLM


class OpenAILLM(BaseLLM):
    """OpenAI 兼容 API（含 OpenClaw Gateway）"""

    def __init__(
        self,
        url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs,
    ):
        self.url = url
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt or (
            "You are a helpful voice assistant. Keep responses concise and conversational. "
            "Aim for 1-2 sentences unless more detail is needed."
        )
        self.request_timeout_s = float(os.getenv("OPENCLAW_BACKEND_TIMEOUT_S", "30"))
        self.enable_http2 = os.getenv("OPENCLAW_BACKEND_HTTP2", "true").lower() == "true"
        self.conversation_history: List[Dict] = []
        self._client = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._setup_client()

    def _setup_client(self):
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.request_timeout_s, connect=5.0),
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=20,
                keepalive_expiry=120.0,
            ),
            http2=self.enable_http2,
        )

        try:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.url,
                http_client=self._http_client,
            )
            logger.info(f"✅ OpenAILLM ready (url={self.url}, model={self.model})")
        except ImportError:
            logger.error("❌ openai package not installed")

    async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        if self._client is None:
            yield "LLM not initialized."
            return

        self.conversation_history.append({"role": "user", "content": user_message})
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.conversation_history[-10:])

        full_response = ""
        logger.info(f"🔍 LLM request: model={self.model}, url={self.url}, messages={len(messages)}")
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                stream=True,
            )
            logger.info(f"✅ LLM stream started")
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_response += text
                    yield text

            self.conversation_history.append(
                {"role": "assistant", "content": full_response}
            )
            logger.info(f"✅ LLM stream complete, response length={len(full_response)}")
        except Exception as e:
            logger.error(f"❌ LLM streaming error: {type(e).__name__}: {e}")
            logger.error(f"   URL: {self.url}")
            logger.error(f"   Model: {self.model}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            yield "Sorry, I had trouble processing that."

    def clear_history(self) -> None:
        self.conversation_history = []

    @property
    def model_name(self) -> str:
        return self.model

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
