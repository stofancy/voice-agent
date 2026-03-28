"""
Booking Agent for Voice Agent.

Specialized agent for hotel and flight booking with hotel tools.
"""

from typing import AsyncGenerator, Dict, List, Optional

from .base import AgentEvent
from .events import (
    AgentStartEvent,
    AgentCompleteEvent,
)
from .langchain_agent import LangChainAgent
from .tools.hotel_tool import get_hotel_tools


BOOKING_PROMPT = """You are a voice booking assistant. Help users book hotels and flights.

For hotels:
- Ask for location, dates, and guest count
- Use search_hotels to find options
- Use book_hotel to confirm booking
- Confirm all details before booking

Keep responses concise for voice interaction. Confirm booking reference at the end."""


class BookingAgent:
    """
    Agent specialized in hotel and flight booking.

    Uses hotel tools and a ReAct-style prompt for booking flows.
    """

    def __init__(
        self,
        llm,
        stream_controller=None,
        tools: Optional[List] = None,
    ):
        self._llm = llm
        self._stream_controller = stream_controller
        self._tools = tools or get_hotel_tools()
        self._conversation_history: List[Dict[str, str]] = []
        self._agent = LangChainAgent(
            agent_type="booking",
            llm=llm,
            tools=self._tools,
            stream_controller=stream_controller,
            system_prompt=BOOKING_PROMPT,
        )

    @property
    def agent_type(self) -> str:
        return "booking"

    async def astream(
        self,
        input_text: str,
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Stream booking agent response with tool events."""
        yield AgentStartEvent(agent_type="booking", input_text=input_text)

        async for event in self._agent.astream(input_text, conversation_history):
            yield event

        yield AgentCompleteEvent(agent_type="booking", full_response="")

    async def ainvoke(
        self,
        input_text: str,
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> str:
        """Invoke booking agent and return complete response."""
        return await self._agent.ainvoke(input_text, conversation_history)
