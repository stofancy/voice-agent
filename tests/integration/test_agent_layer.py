"""
Integration tests for Agent Layer.

Tests the interaction between agent components including:
- LangChainAgent with tools
- AgentRouter with multiple agents
- TurnContext cancellation propagation
- Stream gap measurement
"""

import asyncio
import pytest

try:
    from src.server.agent.langchain_agent import LangChainAgent, TOOL_PROGRESS_MESSAGES
    from src.server.agent.booking_agent import BookingAgent
    from src.server.agent.query_agent import QueryAgent
    from src.server.agent.router import AgentRouter
    from src.server.agent.stream_controller import StreamController
    from src.server.agent.tools.hotel_tool import get_hotel_tools, search_hotels, book_hotel
    from src.server.agent.tools.query_tool import get_query_tools
    from src.server.turn_context import TurnContext

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestAgentRouterIntegration:
    """Integration tests for AgentRouter with real agents."""

    @pytest.fixture
    def booking_agent(self):
        """Create a BookingAgent for testing."""
        return BookingAgent(llm=None)

    @pytest.fixture
    def query_agent(self):
        """Create a QueryAgent for testing."""
        return QueryAgent(llm=None)

    @pytest.fixture
    def router(self, booking_agent, query_agent):
        """Create a router with both agents."""
        return AgentRouter(
            booking_agent=booking_agent,
            query_agent=query_agent,
            default_agent=booking_agent,
        )

    def test_router_with_booking_intent(self, router):
        """Test routing booking intent to BookingAgent."""
        agent = router.route("I want to book a hotel")
        assert agent.agent_type == "booking"

    def test_router_with_query_intent(self, router, query_agent):
        """Test routing query intent to QueryAgent."""
        agent = router.route("What's the weather like?")
        assert agent.agent_type == "query"

    def test_router_with_default_intent(self, router, booking_agent):
        """Test default routing when no intent detected."""
        agent = router.route("Hello there")
        # Should default to booking_agent
        assert agent.agent_type == "booking"

    def test_booking_agent_has_tools(self, booking_agent):
        """Test that BookingAgent has hotel tools."""
        tools = booking_agent._tools
        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "search_hotels" in tool_names
        assert "book_hotel" in tool_names

    def test_query_agent_has_tools(self, query_agent):
        """Test that QueryAgent has query tools."""
        tools = query_agent._tools
        assert len(tools) == 3
        tool_names = [t.name for t in tools]
        assert "get_weather" in tool_names
        assert "web_search" in tool_names
        assert "get_time" in tool_names


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestStreamControllerIntegration:
    """Integration tests for StreamController with callbacks."""

    @pytest.fixture
    def progress_messages(self):
        """Collect progress messages."""
        messages = []

        async def tts_callback(text):
            messages.append(text)

        return tts_callback, messages

    @pytest.fixture
    def ws_events(self):
        """Collect WebSocket events."""
        events = []

        async def ws_callback(event):
            events.append(event)

        return ws_callback, events

    @pytest.mark.asyncio
    async def test_stream_controller_progress_emission(self, progress_messages):
        """Test that emit_progress sends text to TTS callback."""
        tts_callback, messages = progress_messages
        controller = StreamController(tts_callback=tts_callback)

        await controller.emit_progress("Searching for hotels...")
        await asyncio.sleep(0.05)  # Allow async callback to execute

        assert len(messages) == 1
        assert "Searching" in messages[0]

    @pytest.mark.asyncio
    async def test_stream_controller_cancellation(self, progress_messages):
        """Test that cancellation stops progress emission."""
        tts_callback, messages = progress_messages
        controller = StreamController(tts_callback=tts_callback)

        controller.is_cancelled = True
        await controller.emit_progress("This should not be emitted")
        await asyncio.sleep(0.05)

        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_stream_controller_ws_and_tts_callbacks(self, progress_messages, ws_events):
        """Test StreamController with both TTS and WS callbacks."""
        tts_callback, messages = progress_messages
        ws_callback, events = ws_events

        controller = StreamController(
            tts_callback=tts_callback,
            ws_callback=ws_callback,
            turn_id="test-turn-123",
        )

        # Simulate tool start
        controller.on_tool_start(
            serialized={"name": "search_hotels"},
            input_str='{"location": "NYC"}',
        )
        await asyncio.sleep(0.05)

        # Should have TTS callback
        assert len(messages) == 1
        assert "Calling" in messages[0]


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestTurnContextCancellationIntegration:
    """Integration tests for TurnContext cancellation propagation."""

    @pytest.fixture
    def turn_context(self):
        """Create a TurnContext for testing."""
        return TurnContext()

    @pytest.mark.asyncio
    async def test_cancel_sets_is_cancelled(self, turn_context):
        """Test that cancel() sets is_cancelled flag."""
        assert not turn_context.is_cancelled()

        turn_context.cancel()
        assert turn_context.is_cancelled()

    @pytest.mark.asyncio
    async def test_reset_clears_cancellation(self, turn_context):
        """Test that reset() clears cancellation flag."""
        turn_context.cancel()
        assert turn_context.is_cancelled()

        turn_context.reset()
        assert not turn_context.is_cancelled()

    @pytest.mark.asyncio
    async def test_turn_context_has_unique_id(self, turn_context):
        """Test that each TurnContext has a unique ID."""
        ctx2 = TurnContext()
        assert turn_context.turn_id != ctx2.turn_id
        assert len(turn_context.turn_id) == 8


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestToolProgressMessagesIntegration:
    """Integration tests for tool progress messages."""

    def test_all_hotel_tools_have_progress_messages(self):
        """Test that all hotel tools have corresponding progress messages."""
        tools = get_hotel_tools()
        for tool in tools:
            assert tool.name in TOOL_PROGRESS_MESSAGES, f"Missing progress message for {tool.name}"

    def test_all_query_tools_have_progress_messages(self):
        """Test that all query tools have corresponding progress messages."""
        tools = get_query_tools()
        for tool in tools:
            assert tool.name in TOOL_PROGRESS_MESSAGES, f"Missing progress message for {tool.name}"

    def test_progress_messages_are_non_empty(self):
        """Test that all progress messages are non-empty strings."""
        for tool_name, message in TOOL_PROGRESS_MESSAGES.items():
            assert isinstance(message, str)
            assert len(message) > 0


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestAgentStreamingSynthesisIntegration:
    """Integration tests for AgentStreamingSynthesis."""

    def test_agent_streaming_synthesis_import(self):
        """Test that AgentStreamingSynthesis can be imported."""
        from src.server.agent.agent_streaming_synthesis import AgentStreamingSynthesis
        assert AgentStreamingSynthesis is not None

    def test_agent_streaming_synthesis_initialization(self):
        """Test AgentStreamingSynthesis initialization."""
        from src.server.agent.agent_streaming_synthesis import AgentStreamingSynthesis

        # Mock websocket
        class MockWebSocket:
            async def send_json(self, data):
                pass

        synthesis = AgentStreamingSynthesis(
            agent=None,
            tts=None,
            websocket=MockWebSocket(),
        )
        assert synthesis is not None
        assert synthesis._agent is None
        assert synthesis._tts is None


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestCorrelationIdPropagation:
    """Integration tests for correlation ID (turn_id) propagation."""

    def test_stream_controller_accepts_turn_id(self):
        """Test that StreamController accepts turn_id."""
        controller = StreamController(turn_id="test-turn-456")
        assert controller._turn_id == "test-turn-456"

    def test_stream_controller_set_turn_id(self):
        """Test that StreamController.set_turn_id() updates correlation ID."""
        controller = StreamController()
        assert controller._turn_id is None

        controller.set_turn_id("new-turn-id")
        assert controller._turn_id == "new-turn-id"

    def test_langchain_agent_accepts_turn_id(self):
        """Test that LangChainAgent accepts turn_id."""
        agent = LangChainAgent(
            agent_type="test",
            llm=None,
            tools=[],
            turn_id="agent-turn-789",
        )
        assert agent._turn_id == "agent-turn-789"


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestFunctionalSmokeTests:
    """
    Functional smoke tests for agent layer.

    These tests verify the framework works without hanging or deadlocking.
    Since tools are mocks, we don't test performance metrics - just functional correctness.
    """

    @pytest.mark.asyncio
    async def test_mock_tool_executes_without_hang(self):
        """
        Verify mock tools execute and return results within reasonable time.
        Target: <5s for mock tools (real tools would have different expectations).
        """
        import time

        start = time.monotonic()

        # Test search_hotels
        result = await search_hotels.ainvoke({"location": "NYC"})
        assert result is not None
        assert "hotels" in result

        # Test book_hotel
        result = await book_hotel.ainvoke({
            "hotel_id": "h1",
            "guest_name": "Test User",
            "checkin": "2026-04-01",
            "checkout": "2026-04-02",
        })
        assert result is not None
        assert "booking_id" in result

        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"Mock tools took {elapsed:.2f}s, expected <5s"

    @pytest.mark.asyncio
    async def test_stream_controller_cancellation_stops_processing(self):
        """
        Verify cancellation mechanism works - when is_cancelled is True,
        emit_progress does nothing.
        """
        progress_called = False

        async def dummy_callback(text):
            nonlocal progress_called
            progress_called = True

        controller = StreamController(tts_callback=dummy_callback)
        controller.is_cancelled = True

        await controller.emit_progress("This should not be emitted")
        await asyncio.sleep(0.05)

        assert not progress_called, "Progress should not be emitted when cancelled"

    @pytest.mark.asyncio
    async def test_backpressure_queue_drops_oldest_when_full(self):
        """
        Verify backpressure queue drops oldest events when max depth reached.
        """
        from src.server.agent.langchain_agent import BackpressureQueue
        from src.server.agent.events import StreamChunkEvent

        # Create queue with small maxlen for testing
        queue = BackpressureQueue(max_depth=3)

        # Fill the queue
        for i in range(3):
            queue.put_nowait(StreamChunkEvent(text=f"chunk_{i}"))

        # Adding 4th item should drop the oldest (chunk_0)
        queue.put_nowait(StreamChunkEvent(text="chunk_3"))

        # Should have chunk_1, chunk_2, chunk_3
        assert queue.get_nowait().text == "chunk_1"
        assert queue.get_nowait().text == "chunk_2"
        assert queue.get_nowait().text == "chunk_3"

    def test_turn_context_provides_unique_id(self):
        """Verify each TurnContext gets a unique ID."""
        ctx1 = TurnContext()
        ctx2 = TurnContext()
        assert ctx1.turn_id != ctx2.turn_id
        assert len(ctx1.turn_id) == 8

    def test_all_progress_messages_configured(self):
        """Verify all mock tools have corresponding progress messages."""
        hotel_tools = get_hotel_tools()
        query_tools = get_query_tools()

        all_tool_names = [t.name for t in hotel_tools] + [t.name for t in query_tools]

        for name in all_tool_names:
            assert name in TOOL_PROGRESS_MESSAGES, f"Missing progress message for {name}"
            assert len(TOOL_PROGRESS_MESSAGES[name]) > 0

    def test_router_routes_booking_intent_to_booking_agent(self):
        """Verify router correctly routes booking intents."""
        booking_agent = BookingAgent(llm=None)
        query_agent = QueryAgent(llm=None)
        router = AgentRouter(
            booking_agent=booking_agent,
            query_agent=query_agent,
        )

        # Various booking-related phrases
        booking_phrases = [
            "I want to book a hotel",
            "book a flight",
            "reserve a room",
            "make a reservation",
        ]

        for phrase in booking_phrases:
            agent = router.route(phrase)
            assert agent.agent_type == "booking", f"Failed to route: {phrase}"

    def test_router_routes_query_intent_to_query_agent(self):
        """Verify router correctly routes query intents."""
        booking_agent = BookingAgent(llm=None)
        query_agent = QueryAgent(llm=None)
        router = AgentRouter(
            booking_agent=booking_agent,
            query_agent=query_agent,
        )

        # Various query-related phrases
        query_phrases = [
            "what's the weather",
            "search for information",
            "what time is it",
            "how is the weather in Tokyo",
        ]

        for phrase in query_phrases:
            agent = router.route(phrase)
            assert agent.agent_type == "query", f"Failed to route: {phrase}"
