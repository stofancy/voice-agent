"""
Integration tests for booking flow with stream continuity.

Verifies that TTS continues during tool execution.
"""

import pytest

try:
    from src.server.agent.tools.hotel_tool import search_hotels, book_hotel, get_hotel_tools
    from src.server.agent.booking_agent import BookingAgent

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestHotelTools:
    """Tests for hotel tool functions."""

    @pytest.mark.asyncio
    async def test_search_hotels_returns_list(self):
        """search_hotels returns a list of hotels."""
        result = await search_hotels({"location": "NYC"})

        assert "hotels" in result
        assert "count" in result
        assert result["count"] == 2
        assert len(result["hotels"]) == 2

    @pytest.mark.asyncio
    async def test_search_hotels_with_defaults(self):
        """search_hotels works with minimal input."""
        result = await search_hotels({})

        assert result["hotels"][0]["available"] is True

    @pytest.mark.asyncio
    async def test_book_hotel_returns_confirmation(self):
        """book_hotel returns booking confirmation."""
        result = await book_hotel(
            {
                "hotel_id": "h1",
                "guest_name": "John Doe",
                "checkin": "2026-04-01",
                "checkout": "2026-04-02",
            }
        )

        assert "booking_id" in result
        assert result["status"] == "confirmed"
        assert "John Doe" in result["confirmation"]

    def test_get_hotel_tools_returns_list(self):
        """get_hotel_tools returns list of tools."""
        tools = get_hotel_tools()

        assert len(tools) == 2
        assert any(t["name"] == "search_hotels" for t in tools)
        assert any(t["name"] == "book_hotel" for t in tools)


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

        assert "hotel" in TOOL_PROGRESS_MESSAGES
        assert "search" in TOOL_PROGRESS_MESSAGES
        assert "book" in TOOL_PROGRESS_MESSAGES

    def test_hotel_progress_message(self):
        """Hotel progress message is appropriate."""
        from src.server.agent.langchain_agent import TOOL_PROGRESS_MESSAGES

        msg = TOOL_PROGRESS_MESSAGES["hotel"]

        assert "hotel" in msg.lower() or "finding" in msg.lower()
