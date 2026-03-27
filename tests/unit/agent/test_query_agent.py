"""
Tests for QueryAgent.

Verifies QueryAgent initialization and query tool integration.
"""

import pytest

try:
    from src.server.agent import QueryAgent, LANGCHAIN_AVAILABLE
except ImportError:
    LANGCHAIN_AVAILABLE = False


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestQueryAgent:
    """Tests for QueryAgent class."""

    def test_agent_initialization(self):
        """QueryAgent initializes with correct parameters."""
        agent = QueryAgent(
            llm=None,
            stream_controller=None,
        )

        assert agent.agent_type == "query"
        assert agent._llm is None
        assert agent._tools is not None
        assert len(agent._tools) > 0

    def test_agent_type_property(self):
        """agent_type property returns correct value."""
        agent = QueryAgent(llm=None)

        assert agent.agent_type == "query"

    def test_agent_has_query_tools(self):
        """QueryAgent has query tools configured."""
        agent = QueryAgent(llm=None)
        tool_names = {t["name"] for t in agent._tools}

        assert "get_weather" in tool_names
        assert "web_search" in tool_names
        assert "get_time" in tool_names

    def test_agent_with_custom_tools(self):
        """QueryAgent accepts custom tools list."""
        custom_tools = [{"name": "custom", "description": "test", "function": lambda: None}]

        agent = QueryAgent(llm=None, tools=custom_tools)

        assert agent._tools == custom_tools

    def test_agent_has_langchain_agent(self):
        """QueryAgent wraps LangChainAgent internally."""
        agent = QueryAgent(llm=None)

        assert hasattr(agent, "_agent")
        assert agent._agent is not None


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestQueryTools:
    """Tests for query tool functions."""

    def test_get_weather_returns_dict(self):
        """get_weather returns weather information dict."""
        import asyncio
        from src.server.agent.tools.query_tool import get_weather

        result = asyncio.get_event_loop().run_until_complete(get_weather({"location": "Beijing"}))

        assert "location" in result
        assert "temperature" in result
        assert "condition" in result
        assert result["location"] == "Beijing"

    def test_web_search_returns_dict(self):
        """web_search returns search results dict."""
        import asyncio
        from src.server.agent.tools.query_tool import web_search

        result = asyncio.get_event_loop().run_until_complete(web_search({"query": "test query"}))

        assert "query" in result
        assert "results" in result
        assert "count" in result
        assert result["query"] == "test query"

    def test_get_time_returns_dict(self):
        """get_time returns time information dict."""
        import asyncio
        from src.server.agent.tools.query_tool import get_time

        result = asyncio.get_event_loop().run_until_complete(get_time({"timezone": "UTC"}))

        assert "timezone" in result
        assert "time" in result
        assert "date" in result
        assert "formatted" in result

    def test_get_query_tools_returns_list(self):
        """get_query_tools returns list of tool dicts."""
        from src.server.agent.tools.query_tool import get_query_tools

        tools = get_query_tools()

        assert isinstance(tools, list)
        assert len(tools) == 3
        assert all("name" in t for t in tools)
        assert all("description" in t for t in tools)
        assert all("function" in t for t in tools)
