"""
Tests for AgentRouter and routing logic.
"""

import pytest

try:
    from src.server.agent import AgentRouter, LANGCHAIN_AVAILABLE
except ImportError:
    LANGCHAIN_AVAILABLE = False


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestAgentRouter:
    """Tests for AgentRouter intent classification and routing."""

    def test_router_initialization(self):
        """Router initializes with optional agents."""
        router = AgentRouter()
        assert router._booking_agent is None
        assert router._query_agent is None
        assert router._default_agent is None

    def test_router_with_agents(self):
        """Router stores provided agents."""
        mock_booking = object()
        mock_query = object()
        mock_default = object()

        router = AgentRouter(
            booking_agent=mock_booking,
            query_agent=mock_query,
            default_agent=mock_default,
        )

        assert router._booking_agent is mock_booking
        assert router._query_agent is mock_query
        assert router._default_agent is mock_default

    def test_classify_booking_intent(self):
        """Classifies 'book a hotel' as booking intent."""
        router = AgentRouter()
        intent, confidence = router.classify_intent("I want to book a hotel")

        assert intent == "booking"
        assert confidence > 0

    def test_classify_flight_booking(self):
        """Classifies 'book a flight' as booking intent."""
        router = AgentRouter()
        intent, confidence = router.classify_intent("Book me a flight to Shanghai")

        assert intent == "booking"
        assert confidence > 0

    def test_classify_weather_intent(self):
        """Classifies 'what's the weather' as query intent."""
        router = AgentRouter()
        intent, confidence = router.classify_intent("What's the weather in Beijing?")

        assert intent == "query"
        assert confidence > 0

    def test_classify_search_intent(self):
        """Classifies 'search for' as query intent."""
        router = AgentRouter()
        intent, confidence = router.classify_intent("Search for the latest news")

        assert intent == "query"
        assert confidence > 0

    def test_classify_default_intent(self):
        """Classifies generic text as default intent."""
        router = AgentRouter()
        intent, confidence = router.classify_intent("Hello there")

        assert intent == "default"
        assert confidence == 0.5

    def test_route_booking_intent(self):
        """Routes booking intent to booking agent."""
        mock_booking = object()
        mock_query = object()

        router = AgentRouter(
            booking_agent=mock_booking,
            query_agent=mock_query,
        )

        result = router.route("I want to book a hotel")
        assert result is mock_booking

    def test_route_query_intent(self):
        """Routes query intent to query agent."""
        mock_booking = object()
        mock_query = object()

        router = AgentRouter(
            booking_agent=mock_booking,
            query_agent=mock_query,
        )

        result = router.route("What's the weather?")
        assert result is mock_query

    def test_route_default_falls_back_to_booking(self):
        """Falls back to booking agent when no keywords match."""
        mock_booking = object()
        mock_query = object()

        router = AgentRouter(
            booking_agent=mock_booking,
            query_agent=mock_query,
        )

        result = router.route("Hello")
        assert result is mock_booking

    def test_route_raises_when_no_agents(self):
        """Raises ValueError when no agents configured."""
        router = AgentRouter()

        with pytest.raises(ValueError):
            router.route("Hello")

    def test_set_agents_updates_runtime(self):
        """set_agents updates agents at runtime."""
        router = AgentRouter()

        mock_booking = object()
        mock_query = object()

        router.set_agents(
            booking_agent=mock_booking,
            query_agent=mock_query,
        )

        assert router._booking_agent is mock_booking
        assert router._query_agent is mock_query

    def test_set_agents_preserves_existing(self):
        """set_agents doesn't overwrite non-None agents."""
        mock_booking = object()
        mock_query = object()

        router = AgentRouter(
            booking_agent=mock_booking,
            query_agent=mock_query,
        )

        new_booking = object()
        router.set_agents(booking_agent=new_booking)

        assert router._booking_agent is new_booking
        assert router._query_agent is mock_query


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestRouterWithRealAgents:
    """Integration tests for AgentRouter with real BookingAgent and QueryAgent."""

    def test_booking_intent_routes_to_booking_agent(self):
        """T026: Booking intent routes to BookingAgent."""
        from src.server.agent import create_booking_agent, create_query_agent
        from src.server.agent.router import AgentRouter

        booking_agent = create_booking_agent(llm=None)
        query_agent = create_query_agent(llm=None)

        router = AgentRouter(
            booking_agent=booking_agent,
            query_agent=query_agent,
        )

        result = router.route("I want to book a hotel for tomorrow")
        assert result is booking_agent
        assert result.agent_type == "booking"

    def test_query_intent_routes_to_query_agent(self):
        """T026: Query intent routes to QueryAgent."""
        from src.server.agent import create_booking_agent, create_query_agent
        from src.server.agent.router import AgentRouter

        booking_agent = create_booking_agent(llm=None)
        query_agent = create_query_agent(llm=None)

        router = AgentRouter(
            booking_agent=booking_agent,
            query_agent=query_agent,
        )

        result = router.route("What's the weather in Tokyo?")
        assert result is query_agent
        assert result.agent_type == "query"

    def test_reserve_routes_to_booking(self):
        """T026: 'Reserve' keyword routes to booking agent."""
        from src.server.agent import create_booking_agent, create_query_agent
        from src.server.agent.router import AgentRouter

        booking_agent = create_booking_agent(llm=None)
        query_agent = create_query_agent(llm=None)

        router = AgentRouter(
            booking_agent=booking_agent,
            query_agent=query_agent,
        )

        result = router.route("Reserve a room at the Grand Hotel")
        assert result is booking_agent
        assert result.agent_type == "booking"

    def test_find_routes_to_query(self):
        """T026: 'Find' keyword routes to query agent."""
        from src.server.agent import create_booking_agent, create_query_agent
        from src.server.agent.router import AgentRouter

        booking_agent = create_booking_agent(llm=None)
        query_agent = create_query_agent(llm=None)

        router = AgentRouter(
            booking_agent=booking_agent,
            query_agent=query_agent,
        )

        result = router.route("Find information about Paris")
        assert result is query_agent
        assert result.agent_type == "query"

    def test_hotel_keyword_routes_to_booking(self):
        """T026: 'Hotel' keyword routes to booking agent."""
        from src.server.agent import create_booking_agent, create_query_agent
        from src.server.agent.router import AgentRouter

        booking_agent = create_booking_agent(llm=None)
        query_agent = create_query_agent(llm=None)

        router = AgentRouter(
            booking_agent=booking_agent,
            query_agent=query_agent,
        )

        result = router.route("I need a hotel near the beach")
        assert result is booking_agent
        assert result.agent_type == "booking"

    def test_time_query_routes_to_query(self):
        """T026: Time-related query routes to query agent."""
        from src.server.agent import create_booking_agent, create_query_agent
        from src.server.agent.router import AgentRouter

        booking_agent = create_booking_agent(llm=None)
        query_agent = create_query_agent(llm=None)

        router = AgentRouter(
            booking_agent=booking_agent,
            query_agent=query_agent,
        )

        result = router.route("What time is it in London?")
        assert result is query_agent
        assert result.agent_type == "query"
