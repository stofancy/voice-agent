"""Gemini LLM — via OpenAI-compatible endpoint."""

import os
from typing import AsyncGenerator, Dict, List, Optional

import httpx
from loguru import logger

from .base import BaseLLM


MAX_HISTORY_SIZE = 20  # Keep last 20 messages to prevent memory leak


class GeminiLLM(BaseLLM):
    """Gemini via OpenAI-compatible API"""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt or (
            "You are a helpful voice assistant. Keep responses concise and conversational. "
            "Aim for 1-2 sentences unless more detail is needed."
        )
        self.request_timeout_s = float(os.getenv("OPENCLAW_BACKEND_TIMEOUT_S", "30"))
        self.conversation_history: List[Dict] = []
        self._http_client: Optional[httpx.AsyncClient] = None
        self._setup_client()

    def _setup_client(self):
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.request_timeout_s, connect=5.0),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        )
        logger.info(f"✅ GeminiLLM ready (url={self.base_url}, model={self.model})")

    async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        if self._http_client is None:
            yield "LLM not initialized."
            return

        self.conversation_history.append({"role": "user", "content": user_message})
        # Trim history to prevent memory leak
        if len(self.conversation_history) > MAX_HISTORY_SIZE:
            self.conversation_history = self.conversation_history[-MAX_HISTORY_SIZE:]
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.conversation_history[-10:])

        full_response = ""
        try:
            response = await self._http_client.post(
                f"{self.base_url}chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 500,
                    "temperature": 0.7,
                    "stream": True,
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()

            async for line in response.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    import json
                    chunk_data = json.loads(data)
                    if chunk_data.get("choices"):
                        content = chunk_data["choices"][0]["delta"].get("content")
                        if content:
                            full_response += content
                            yield content

            self.conversation_history.append({"role": "assistant", "content": full_response})
            # Trim history to prevent memory leak
            if len(self.conversation_history) > MAX_HISTORY_SIZE:
                self.conversation_history = self.conversation_history[-MAX_HISTORY_SIZE:]
        except Exception as e:
            logger.error(f"Gemini LLM streaming error: {e}")
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
