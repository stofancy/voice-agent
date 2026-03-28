"""
Integration tests for VoiceBookingAgent with Stage Tools.

Tests the full flow: user NL input → LLM interpretation → Stage Tool execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.server.agent.voice_booking_agent import VoiceBookingAgent, BookingState
from src.server.agent.tools.stage_tool_wrapper import (
    get_all_langchain_tools,
    create_search_tool_wrapper,
    create_select_hotel_tool_wrapper,
)
from src.server.browser.stages.base import StageAction


class MockBrowserController:
    """Mock BrowserController for testing."""

    def __init__(self):
        self.current_url = "https://www.booking.com"
        self.navigate_calls = []
        self.evaluate_script_calls = []

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def navigate(self, url):
        self.navigate_calls.append(url)
        self.current_url = url

    async def evaluate_script(self, script):
        self.evaluate_script_calls.append(script)
        if "window.location.href" in script:
            return self.current_url
        elif "hotel" in script.lower():
            return [
                {"name": "Test Hotel A", "price": "CNY 1,000", "score": "9.0", "url": "https://booking.com/hotel/a"},
                {"name": "Test Hotel B", "price": "CNY 2,000", "score": "9.5", "url": "https://booking.com/hotel/b"},
            ]
        return None

    async def extract_hotel_data(self):
        return [
            {"name": "Test Hotel A", "price": "CNY 1,000", "score": "9.0", "url": "https://booking.com/hotel/a"},
            {"name": "Test Hotel B", "price": "CNY 2,000", "score": "9.5", "url": "https://booking.com/hotel/b"},
        ]


class TestBookingState:
    """Tests for BookingState."""

    def test_initial_state(self):
        """Test initial booking state."""
        state = BookingState("test-session")
        assert state.session_id == "test-session"
        assert state.current_stage_index == 0
        assert state.current_stage == "search"
        assert not state.is_complete

    def test_stage_progression(self):
        """Test stage progression."""
        state = BookingState("test-session")
        assert state.current_stage == "search"

        state.current_stage_index = 1
        assert state.current_stage == "select_hotel"

        # index 6 is the last stage (finalize), not complete until after execution
        state.current_stage_index = 6
        assert not state.is_complete

        # After all stages, is_complete becomes True
        state.current_stage_index = 7
        assert state.is_complete


class TestStageToolWrappers:
    """Tests for stage tool wrappers."""

    @pytest.mark.asyncio
    async def test_search_tool_wrapper(self):
        """Test search tool wrapper execution."""
        mock_bc = MockBrowserController()
        wrapper = create_search_tool_wrapper()

        result = await wrapper.execute(
            {
                "location": "Tokyo",
                "checkin": "2026-04-01",
                "checkout": "2026-04-05",
                "guests": 2,
            },
            browser_controller=mock_bc,
        )

        assert result.success is True
        assert "Tokyo" in result.message or "hotels" in result.message.lower()

    @pytest.mark.asyncio
    async def test_select_hotel_tool_wrapper(self):
        """Test select hotel wrapper returns options."""
        wrapper = create_select_hotel_tool_wrapper()

        # Without browser, returns error or empty
        result = await wrapper.execute(
            {"selected_index": 1},
            browser_controller=None,
        )

        # Should handle gracefully
        assert result is not None


class TestVoiceBookingAgent:
    """Tests for VoiceBookingAgent."""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def mock_bc(self):
        """Mock browser controller."""
        return MockBrowserController()

    @pytest.fixture
    def agent(self, mock_llm, mock_bc):
        """Create agent with mocks."""
        return VoiceBookingAgent(
            llm=mock_llm,
            browser_controller=mock_bc,
            stream_controller=None,
        )

    def test_agent_initialization(self, agent):
        """Test agent initializes with tools."""
        assert len(agent._tools) > 0
        assert "search_hotels" in agent._tool_map
        assert "select_hotel" in agent._tool_map
        assert "navigate_to_hotel" in agent._tool_map
        assert "finalize_booking" in agent._tool_map

    def test_get_state(self, agent):
        """Test getting booking state (returns None for non-existent session)."""
        state = agent.get_state("non-existent-session")
        assert state is None

        # Create state first
        state = agent._get_or_create_state("new-session")
        assert state is not None
        assert state.session_id == "new-session"
        assert state.current_stage == "search"

    def test_reset_session(self, agent):
        """Test session reset."""
        agent._session_states["test-session"] = BookingState("test-session")
        agent.reset_session("test-session")
        assert agent.get_state("test-session") is None

    @pytest.mark.asyncio
    async def test_execute_search_stage(self, agent, mock_bc):
        """Test direct stage execution."""
        result = await agent.execute_stage(
            "search_hotels",
            {
                "location": "Tokyo",
                "checkin": "2026-04-01",
                "checkout": "2026-04-05",
                "guests": 2,
            },
            session_id="test-session",
        )

        assert result.success is True
        assert mock_bc.navigate_calls[-1] == "https://www.booking.com"

    @pytest.mark.asyncio
    async def test_booking_state_persistence(self, agent):
        """Test booking state persists across calls."""
        session_id = "test-persist"

        # Execute search
        await agent.execute_stage(
            "search_hotels",
            {"location": "Tokyo"},
            session_id=session_id,
        )

        # Check state - completed_stages contains tool_name
        state = agent.get_state(session_id)
        assert state is not None
        assert "search_hotels" in state["completed_stages"]


class TestNLCSelection:
    """Tests for NL selection handling."""

    @pytest.fixture
    def agent(self):
        """Create agent with mocks."""
        mock_llm = AsyncMock()
        mock_bc = MockBrowserController()
        return VoiceBookingAgent(
            llm=mock_llm,
            browser_controller=mock_bc,
            stream_controller=None,
        )

    @pytest.mark.asyncio
    async def test_index_selection(self, agent):
        """Test index-based selection parsing."""
        # Setup state with options - need to set current_stage to select_hotel
        session_id = "test-index"
        state = agent._get_or_create_state(session_id)
        state.current_stage_index = 1  # select_hotel stage
        state.selected_options["select_hotel"] = [
            {"index": 1, "name": "Hotel A"},
            {"index": 2, "name": "Hotel B"},
            {"index": 3, "name": "Hotel C"},
        ]

        result = await agent._handle_selection("第二个", session_id)

        assert result.success is True
        assert result.data.get("selected", {}).get("name") == "Hotel B"

    @pytest.mark.asyncio
    async def test_preference_selection_price(self, agent):
        """Test price preference selection."""
        session_id = "test-price"
        state = agent._get_or_create_state(session_id)
        state.current_stage_index = 1  # select_hotel stage
        state.selected_options["select_hotel"] = [
            {"index": 1, "name": "Cheap Hotel", "details": {"price": "CNY 500"}},
            {"index": 2, "name": "Expensive Hotel", "details": {"price": "CNY 2000"}},
            {"index": 3, "name": "Medium Hotel", "details": {"price": "CNY 1000"}},
        ]

        result = await agent._handle_selection("贵一点的", session_id)

        assert result.success is True
        assert "Expensive" in result.data.get("selected", {}).get("name", "")

    @pytest.mark.asyncio
    async def test_preference_selection_rating(self, agent):
        """Test rating preference selection."""
        session_id = "test-rating"
        state = agent._get_or_create_state(session_id)
        state.current_stage_index = 1  # select_hotel stage
        state.selected_options["select_hotel"] = [
            {"index": 1, "name": "Low Rated", "details": {"score": "7.0"}},
            {"index": 2, "name": "High Rated", "details": {"score": "9.5"}},
            {"index": 3, "name": "Medium Rated", "details": {"score": "8.0"}},
        ]

        result = await agent._handle_selection("评分最高的", session_id)

        assert result.success is True
        assert "High Rated" in result.data.get("selected", {}).get("name", "")


class TestLangChainTools:
    """Tests that all tools can be converted to LangChain tools."""

    def test_all_wrappers_have_langchain_tool(self):
        """Test each wrapper produces valid LC tool."""
        from src.server.agent.tools.stage_tool_wrapper import (
            create_search_tool_wrapper,
            create_select_hotel_tool_wrapper,
            create_select_room_tool_wrapper,
            create_confirm_selection_tool_wrapper,
            create_fill_guest_tool_wrapper,
            create_finalize_tool_wrapper,
        )

        wrappers = [
            create_search_tool_wrapper(),
            create_select_hotel_tool_wrapper(),
            create_select_room_tool_wrapper(),
            create_confirm_selection_tool_wrapper(),
            create_fill_guest_tool_wrapper(),
            create_finalize_tool_wrapper(),
        ]

        for wrapper in wrappers:
            tool = wrapper.to_langchain_tool()
            assert tool.name == wrapper.name
            assert tool.description
            assert tool.args_schema
