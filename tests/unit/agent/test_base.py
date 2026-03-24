"""
Unit tests for BaseAgent and AgentEvent.
"""

import pytest
from abc import ABC


class TestAgentEvent:
    """Tests for AgentEvent dataclass - no langchain dependency."""

    def test_agent_event_creation(self):
        """AgentEvent stores event_type and data."""
        from src.server.agent.base import AgentEvent

        event = AgentEvent("test_type", {"key": "value"})

        assert event.event_type == "test_type"
        assert event.data == {"key": "value"}

    def test_agent_event_repr(self):
        """AgentEvent has readable repr."""
        from src.server.agent.base import AgentEvent

        event = AgentEvent("test", {"a": 1})
        repr_str = repr(event)

        assert "test" in repr_str


class TestBaseAgentAbstract:
    """Tests that BaseAgent is properly abstract."""

    def test_base_agent_is_abc(self):
        """BaseAgent must be ABC."""
        from src.server.agent.base import BaseAgent

        assert issubclass(BaseAgent, ABC)

    def test_base_agent_cannot_instantiate(self):
        """Direct instantiation of BaseAgent should fail."""
        from src.server.agent.base import BaseAgent

        with pytest.raises(TypeError):
            BaseAgent()


class TestMockAgent:
    """Tests for a mock implementation of BaseAgent."""

    @pytest.mark.asyncio
    async def test_mock_agent_astream(self):
        """Mock agent can implement astream."""
        from src.server.agent.base import BaseAgent, AgentEvent

        class MockAgent(BaseAgent):
            @property
            def agent_type(self) -> str:
                return "mock"

            async def astream(self, input_text, conversation_history=None):
                yield AgentEvent("test", {"text": f"response to: {input_text}"})

            async def ainvoke(self, input_text, conversation_history=None) -> str:
                return f"response to: {input_text}"

        agent = MockAgent()
        assert agent.agent_type == "mock"

        events = []
        async for event in agent.astream("hello"):
            events.append(event)

        assert len(events) == 1
        assert events[0].event_type == "test"

    @pytest.mark.asyncio
    async def test_mock_agent_ainvoke(self):
        """Mock agent can implement ainvoke."""
        from src.server.agent.base import BaseAgent

        class MockAgent(BaseAgent):
            @property
            def agent_type(self) -> str:
                return "mock"

            async def astream(self, input_text, conversation_history=None):
                yield "response"

            async def ainvoke(self, input_text, conversation_history=None) -> str:
                return f"response to: {input_text}"

        agent = MockAgent()
        result = await agent.ainvoke("hello")

        assert isinstance(result, str)
        assert result == "response to: hello"
