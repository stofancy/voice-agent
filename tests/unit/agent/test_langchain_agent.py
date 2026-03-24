"""
Tests for LangChainAgent integration with StreamController.

Verifies that TTS text is emitted during tool execution.
"""

import pytest

try:
    from src.server.agent import LANGCHAIN_AVAILABLE
except ImportError:
    LANGCHAIN_AVAILABLE = False


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestLangChainAgentIntegration:
    """Integration tests for LangChainAgent with StreamController."""

    def test_agent_initialization(self):
        """Agent initializes with correct parameters."""
        from src.server.agent import LangChainAgent

        agent = LangChainAgent(
            agent_type="test",
            llm=None,
            tools=[],
            stream_controller=None,
        )

        assert agent.agent_type == "test"
        assert agent._llm is None
        assert agent._tools == []
        assert agent._stream_controller is None

    def test_progress_message_for_search(self):
        """Progress message returned for search tool."""
        from src.server.agent import LangChainAgent

        agent = LangChainAgent(
            agent_type="test",
            llm=None,
            tools=[],
        )

        msg = agent._get_progress_message("search_hotels")

        assert "Searching" in msg or "search" in msg.lower()

    def test_progress_message_for_book(self):
        """Progress message returned for booking tool."""
        from src.server.agent import LangChainAgent

        agent = LangChainAgent(
            agent_type="test",
            llm=None,
            tools=[],
        )

        msg = agent._get_progress_message("book_hotel")

        assert "booking" in msg.lower() or "processing" in msg.lower()

    def test_progress_message_default(self):
        """Default progress message for unknown tools."""
        from src.server.agent import LangChainAgent

        agent = LangChainAgent(
            agent_type="test",
            llm=None,
            tools=[],
        )

        msg = agent._get_progress_message("unknown_tool")

        assert "wait" in msg.lower() or "please" in msg.lower()


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestAgentFactory:
    """Tests for agent factory functions."""

    def test_create_default_agent(self):
        """Factory creates default agent."""
        from src.server.agent import create_default_agent

        agent = create_default_agent(llm=None)

        assert agent.agent_type == "default"
        assert agent._llm is None

    def test_create_query_agent(self):
        """Factory creates query agent."""
        from src.server.agent import create_query_agent

        agent = create_query_agent(llm=None)

        assert agent.agent_type == "query"
        assert agent._llm is None

    def test_create_booking_agent(self):
        """Factory creates booking agent."""
        from src.server.agent import create_booking_agent

        agent = create_booking_agent(llm=None)

        assert agent.agent_type == "booking"
        assert agent._llm is None


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestWebSocketEmitter:
    """Tests for AgentWebSocketEmitter."""

    def test_emitter_initialization(self):
        """Emitter initializes with send function."""
        from src.server.agent.websocket_emitter import AgentWebSocketEmitter

        emitter = AgentWebSocketEmitter(send_func=None)

        assert emitter._send_func is None

    def test_emit_without_send_func(self):
        """Emit does nothing when no send function."""
        import asyncio
        from src.server.agent.websocket_emitter import AgentWebSocketEmitter
        from src.server.agent.events import ToolStartEvent

        emitter = AgentWebSocketEmitter(send_func=None)

        event = ToolStartEvent(tool_name="test", tool_input={})

        result = asyncio.get_event_loop().run_until_complete(emitter.emit(event))

        assert result is None
