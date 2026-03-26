"""
Query Agent for Voice Agent.

Specialized agent for information queries like weather and search.
"""

from typing import AsyncGenerator, Dict, List, Optional

from .base import AgentEvent
from .events import (
    AgentStartEvent,
    AgentCompleteEvent,
)
from .langchain_agent import LangChainAgent
from .tools.query_tool import get_query_tools


QUERY_PROMPT = """You are a voice query assistant. Help users get information about weather, search the web, and answer questions.

For queries:
- Use get_weather to check weather for a location
- Use web_search to find information online
- Use get_time to check current time

Keep responses concise for voice interaction."""


class QueryAgent:
    """
    Agent specialized in information queries.

    Uses query tools (weather, search, time) for information retrieval.
    """

    def __init__(
        self,
        llm,
        stream_controller=None,
        tools: Optional[List] = None,
    ):
        self._llm = llm
        self._stream_controller = stream_controller
        self._tools = tools or get_query_tools()
        self._conversation_history: List[Dict[str, str]] = []
        self._agent = LangChainAgent(
            agent_type="query",
            llm=llm,
            tools=self._tools,
            stream_controller=stream_controller,
            system_prompt=QUERY_PROMPT,
        )

    @property
    def agent_type(self) -> str:
        return "query"

    async def astream(
        self,
        input_text: str,
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Stream query agent response with tool events."""
        yield AgentStartEvent(agent_type="query", input_text=input_text)

        async for event in self._agent.astream(input_text, conversation_history):
            yield event

        yield AgentCompleteEvent(agent_type="query", full_response="")

    async def ainvoke(
        self,
        input_text: str,
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> str:
        """Invoke query agent and return complete response."""
        return await self._agent.ainvoke(input_text, conversation_history)
