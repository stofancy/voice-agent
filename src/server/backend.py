"""
AI Backend module - connects to OpenAI, OpenClaw gateway, or custom backends.
"""

import asyncio
import json
import os
from typing import Optional, List, Dict, AsyncGenerator

from loguru import logger
import httpx


class AIBackend:
    """AI backend for processing user messages."""
    
    def __init__(
        self,
        backend_type: str = "openai",
        url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        self.backend_type = backend_type
        self.url = url
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt or (
            "You are a helpful voice assistant. Keep responses concise and conversational. "
            "Aim for 1-2 sentences unless more detail is needed."
        )
        self.conversation_history: List[Dict] = []
        self._client = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._setup_client()
    
    def _setup_client(self):
        """Set up the API client."""
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=5.0),
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=20,
                keepalive_expiry=120.0,
            ),
            http2=False,
        )

        if self.backend_type == "openai":
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.url if self.url != "https://api.openai.com/v1" else None,
                    http_client=self._http_client,
                )
                logger.info(f"✅ OpenAI client ready (model: {self.model})")
            except ImportError:
                logger.error("openai package not installed")
        elif self.backend_type == "openclaw":
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.url,
                    http_client=self._http_client,
                )
                logger.info(f"✅ OpenClaw Gateway client ready (url: {self.url}, model: {self.model})")
            except ImportError:
                logger.error("openai package not installed")
        else:
            logger.warning(f"Unknown backend type: {self.backend_type}")
    
    async def chat(self, user_message: str) -> str:
        if self.backend_type == "openai" and self._client:
            return await self._chat_openai(user_message)
        else:
            return f"I heard you say: {user_message}"
    
    async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        if self.backend_type in ("openai", "openclaw") and self._client:
            async for chunk in self._chat_openai_stream(user_message):
                yield chunk
        else:
            yield f"I heard you say: {user_message}"
    
    async def _chat_openai(self, user_message: str) -> str:
        self.conversation_history.append({"role": "user", "content": user_message})
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.conversation_history[-10:])
        
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )
            assistant_message = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            return assistant_message
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return "Sorry, I had trouble processing that. Could you try again?"
    
    async def _chat_openai_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        """Stream chat via httpx directly (bypass OpenAI SDK streaming issues)."""
        logger.info(f"🤖 LLM streaming request: {user_message[:50]}...")
        
        self.conversation_history.append({"role": "user", "content": user_message})
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.conversation_history[-10:])
        
        logger.info(f"📝 Messages: {len(messages)} total, sending to {self.model}")
        full_response = ""
        chunk_count = 0
        
        try:
            api_url = str(self._client.base_url).rstrip('/') + '/chat/completions'
            logger.info(f"🔗 Request URL: {api_url}")
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as stream_client:
                async with stream_client.stream(
                    "POST",
                    api_url,
                    headers={
                        "Authorization": f"Bearer {self._client.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 500,
                        "temperature": 0.7,
                        "stream": True,
                    },
                    timeout=60.0
                ) as response:
                    logger.info(f"✅ LLM stream opened (status: {response.status_code}), receiving chunks...")
                    
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        
                        content = line[6:]
                        if content == "[DONE]":
                            logger.info("🏁 [DONE] received")
                            break
                        
                        chunk_count += 1
                        try:
                            data = json.loads(content)
                            choice = data.get("choices", [{}])[0]
                            delta = choice.get("delta", {})
                            text = delta.get("content", "")
                            role = delta.get("role", "")
                            finish_reason = choice.get("finish_reason", "")
                            
                            logger.info(f"📦 Chunk #{chunk_count}: role={repr(role)}, content={repr(text)}, finish={repr(finish_reason)}")
                            
                            if text:
                                full_response += text
                                logger.info(f"📤 LLM chunk #{chunk_count}: {text[:50]}...")
                                yield text
                            elif role:
                                logger.info(f"📋 Chunk #{chunk_count} is role declaration: {role}")
                            elif finish_reason:
                                logger.info(f"🏁 Chunk #{chunk_count} finish_reason: {finish_reason}")
                        except json.JSONDecodeError as e:
                            logger.warning(f"⚠️ Failed to parse chunk JSON: {e}, content: {content[:200]}")
            
            logger.info(f"✅ LLM stream complete: {chunk_count} chunks, {len(full_response)} chars")
            self.conversation_history.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            logger.error(f"❌ httpx streaming error: {e}", exc_info=True)
            yield "Sorry, I had trouble processing that."
    
    def clear_history(self):
        self.conversation_history = []

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
