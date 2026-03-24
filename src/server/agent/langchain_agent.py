"""
LangChain Agent wrapper for Voice Agent.

Wraps LangChain agent with astream_events() for non-blocking tool execution.
"""

from typing import AsyncGenerator, Dict, List, Any, Optional

from .base import BaseAgent, AgentEvent
from .events import StreamChunkEvent, ToolStartEvent, ToolCompleteEvent


class LangChainAgent(BaseAgent):
    """
    LangChain agent wrapper with streaming support.

    Uses astream_events() to emit tool events without blocking the stream.
    """

    def __init__(
        self,
        agent_type: str,
        llm,
        tools: List[Any],
        stream_controller=None,
        system_prompt: Optional[str] = None,
    ):
        self._agent_type = agent_type
        self._llm = llm
        self._tools = tools
        self._stream_controller = stream_controller
        self._system_prompt = system_prompt or "You are a helpful voice assistant."
        self._conversation_history: List[Dict[str, str]] = []

    @property
    def agent_type(self) -> str:
        return self._agent_type

    async def astream(
        self,
        input_text: str,
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Stream agent response with tool events.

        Uses LangChain's astream_events for non-blocking tool execution.
        """
        messages = conversation_history or self._conversation_history
        messages.append({"role": "user", "content": input_text})

        try:
            async for event in self._llm.astream_events({"messages": messages}):
                event_type = event.get("event")

                if event_type == "on_llm_stream":
                    token = event.get("data", {}).get("chunk", {}).get("content", "")
                    if token:
                        yield StreamChunkEvent(text=token)

                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    yield ToolStartEvent(tool_name=tool_name, tool_input=event.get("data", {}))

                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    output = event.get("data", {}).get("output", {})
                    yield ToolCompleteEvent(tool_name=tool_name, tool_output=output)

        finally:
            self._conversation_history.append({"role": "user", "content": input_text})

    async def ainvoke(
        self,
        input_text: str,
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> str:
        """Invoke agent and return complete response."""
        messages = conversation_history or self._conversation_history
        messages.append({"role": "user", "content": input_text})

        response = ""
        async for event in self.astream(input_text, messages):
            if isinstance(event, StreamChunkEvent):
                response += event.text

        self._conversation_history.append({"role": "assistant", "content": response})
        return response
