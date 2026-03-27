"""
Integration tests for booking flow with stream continuity.

Verifies that TTS continues during tool execution.
"""

import json
import pytest

try:
    from src.server.agent.tools.hotel_tool import search_hotels, book_hotel, get_hotel_tools
    from src.server.agent.booking_agent import BookingAgent

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestHotelTools:
    """Tests for hotel tool functions using LangChain @tool format."""

    @pytest.mark.asyncio
    async def test_search_hotels_returns_json(self):
        """search_hotels returns hotel list as JSON string."""
        result = await search_hotels.ainvoke({"location": "NYC"})
        result_dict = json.loads(result)

        assert "hotels" in result_dict
        assert "count" in result_dict
        assert result_dict["count"] == 2
        assert len(result_dict["hotels"]) == 2

    @pytest.mark.asyncio
    async def test_search_hotels_with_defaults(self):
        """search_hotels works with minimal input."""
        result = await search_hotels.ainvoke({})
        result_dict = json.loads(result)

        assert result_dict["hotels"][0]["available"] is True

    @pytest.mark.asyncio
    async def test_book_hotel_returns_confirmation(self):
        """book_hotel returns booking confirmation."""
        result = await book_hotel.ainvoke(
            {
                "hotel_id": "h1",
                "guest_name": "John Doe",
                "checkin": "2026-04-01",
                "checkout": "2026-04-02",
            }
        )
        result_dict = json.loads(result)

        assert "booking_id" in result_dict
        assert result_dict["status"] == "confirmed"
        assert "John Doe" in result_dict["confirmation"]

    def test_get_hotel_tools_returns_list(self):
        """get_hotel_tools returns list of LangChain tools."""
        tools = get_hotel_tools()

        assert len(tools) == 2
        assert any(t.name == "search_hotels" for t in tools)
        assert any(t.name == "book_hotel" for t in tools)


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestBookingAgent:
    """Tests for BookingAgent."""

    def test_booking_agent_initialization(self):
        """BookingAgent initializes correctly."""
        agent = BookingAgent(llm=None)

        assert agent.agent_type == "booking"
        assert agent._llm is None

    def test_booking_agent_has_tools(self):
        """BookingAgent has hotel tools."""
        agent = BookingAgent(llm=None)

        assert len(agent._tools) == 2


class TestStreamContinuity:
    """Tests for stream continuity during tool calls."""

    def test_tool_progress_messages_defined(self):
        """Tool progress messages are defined for hotel tools."""
        from src.server.agent.langchain_agent import TOOL_PROGRESS_MESSAGES

        assert "search_hotels" in TOOL_PROGRESS_MESSAGES
        assert "book_hotel" in TOOL_PROGRESS_MESSAGES

    def test_hotel_progress_message(self):
        """Hotel progress message is appropriate."""
        from src.server.agent.langchain_agent import TOOL_PROGRESS_MESSAGES

        msg = TOOL_PROGRESS_MESSAGES["search_hotels"]

        assert "hotel" in msg.lower() or "search" in msg.lower() or "finding" in msg.lower()
