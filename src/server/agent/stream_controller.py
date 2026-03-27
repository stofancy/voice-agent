"""
StreamController for non-blocking tool event handling.

Integrates with LangChain's BaseCallbackHandler to emit tool events
without blocking the LLM stream.
"""

import asyncio
from typing import Any, Dict, List

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from .events import (
    ToolStartEvent,
    ToolCompleteEvent,
    ToolErrorEvent,
)


class StreamController(BaseCallbackHandler):
    """
    LangChain callback handler for streaming tool events.

    This controller intercepts LangChain agent events and emits
    them to maintain continuous streaming to TTS.

    Attributes:
        tts_callback: Callback function to emit TTS text
        is_cancelled: Cancellation flag
    """

    def __init__(
        self,
        tts_callback=None,
        ws_callback=None,
    ):
        self.tts_callback = tts_callback
        self.ws_callback = ws_callback
        self.is_cancelled = False
        self._current_tool = None

    def reset(self):
        """Reset state for new conversation."""
        self.is_cancelled = False
        self._current_tool = None

    def check_cancelled(self) -> bool:
        """Check if operation should be cancelled."""
        return self.is_cancelled

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs,
    ) -> None:
        """Called when LLM starts generating."""
        if self.tts_callback and not self.is_cancelled:
            asyncio.create_task(self.tts_callback("Let me think..."))

    def on_llm_new_token(
        self,
        token: str,
        **kwargs,
    ) -> None:
        """Called for each new token from LLM."""
        if self.tts_callback and not self.is_cancelled:
            asyncio.create_task(self.tts_callback(token))

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Called when LLM finishes."""
        pass

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs,
    ) -> None:
        """Called when a tool starts execution."""
        if self.is_cancelled:
            return

        tool_name = serialized.get("name", "unknown")
        self._current_tool = tool_name

        if self.ws_callback:
            event = ToolStartEvent(tool_name=tool_name, tool_input={"input": input_str})
            asyncio.create_task(self.ws_callback(event.to_dict()))

        if self.tts_callback:
            asyncio.create_task(self.tts_callback(f"Calling {tool_name}..."))

    def on_tool_end(
        self,
        output: str,
        **kwargs,
    ) -> None:
        """Called when a tool finishes execution."""
        if self.is_cancelled:
            return

        tool_name = self._current_tool or "unknown"

        if self.ws_callback:
            event = ToolCompleteEvent(tool_name=tool_name, tool_output=output)
            asyncio.create_task(self.ws_callback(event.to_dict()))

        if self.tts_callback:
            asyncio.create_task(self.tts_callback(f"{tool_name} completed. "))

        self._current_tool = None

    def on_tool_error(
        self,
        error: Exception,
        **kwargs,
    ) -> None:
        """Called when a tool fails."""
        tool_name = self._current_tool or "unknown"

        if self.ws_callback:
            event = ToolErrorEvent(tool_name=tool_name, error=str(error))
            asyncio.create_task(self.ws_callback(event.to_dict()))

        if self.tts_callback:
            asyncio.create_task(self.tts_callback(f"Sorry, {tool_name} failed. "))

        self._current_tool = None

    async def emit_progress(self, text: str) -> None:
        """Emit progress text to TTS."""
        if self.tts_callback and not self.is_cancelled:
            await self.tts_callback(text)
