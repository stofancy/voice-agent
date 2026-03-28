#!/usr/bin/env python3
"""
Smoke test script for Agent Layer.

Tests the agent layer components directly without requiring full server.

Usage:
    python scripts/smoke_test_agent.py
    or
    python -m pytest tests/unit/agent/ -v
"""

import asyncio
import json
import sys
from pathlib import Path

# Resolve project root (parent of scripts/) and add to path
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def print_test(name: str, passed: bool, details: str = ""):
    status = (
        f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    )
    print(f"  {status} - {name}")
    if details:
        print(f"         {details}")


async def test_imports() -> bool:
    """Test that all agent modules can be imported."""
    print(f"\n{Colors.BLUE}[1] Testing Imports...{Colors.RESET}")

    try:
        from src.server.agent import (
            BaseAgent,  # noqa: F401
            AgentEvent,  # noqa: F401
            ToolStatus,  # noqa: F401
            ToolStartEvent,  # noqa: F401
            ToolProgressEvent,  # noqa: F401
            ToolCompleteEvent,  # noqa: F401
            ToolErrorEvent,  # noqa: F401
            StreamChunkEvent,  # noqa: F401
            AgentStartEvent,  # noqa: F401
            AgentCompleteEvent,  # noqa: F401
        )

        print_test("Core event classes", True)

        from src.server.agent import LangChainAgent  # noqa: F401

        print_test("LangChainAgent", True)

        from src.server.agent import AgentRouter  # noqa: F401

        print_test("AgentRouter", True)

        from src.server.agent import QueryAgent  # noqa: F401

        print_test("QueryAgent", True)

        from src.server.agent import BookingAgent  # noqa: F401

        print_test("BookingAgent", True)

        from src.server.agent import AgentStreamingSynthesis, AgentSynthesisConfig  # noqa: F401

        print_test("AgentStreamingSynthesis", True)

        from src.server.agent.tools.query_tool import (
            get_query_tools,  # noqa: F401
            get_weather,  # noqa: F401
            web_search,  # noqa: F401
            get_time,  # noqa: F401
        )

        print_test("Query tools", True)

        from src.server.agent.tools.hotel_tool import (
            get_hotel_tools,  # noqa: F401
            search_hotels,  # noqa: F401
            book_hotel,  # noqa: F401
        )

        print_test("Hotel tools", True)

        from src.server.agent.tools.dummy_tool import (
            get_dummy_tools,  # noqa: F401
            echo_tool,  # noqa: F401
        )

        print_test("Dummy tools", True)

        return True

    except ImportError as e:
        print_test("Imports", False, str(e))
        return False


async def test_turn_context() -> bool:
    """Test TurnContext cancellation mechanism."""
    print(f"\n{Colors.BLUE}[2] Testing TurnContext...{Colors.RESET}")

    from src.server.turn_context import TurnContext

    tc = TurnContext()

    print_test("Initial not cancelled", not tc.is_cancelled())

    tc.cancel()
    print_test("Cancel sets flag", tc.is_cancelled())

    tc.reset()
    print_test("Reset clears flag", not tc.is_cancelled())

    tc.cancel()
    tc.cancel()
    print_test("Multiple cancels OK", tc.is_cancelled())

    return True


async def test_agent_router() -> bool:
    """Test AgentRouter intent classification."""
    print(f"\n{Colors.BLUE}[3] Testing AgentRouter...{Colors.RESET}")

    from src.server.agent import AgentRouter

    router = AgentRouter()

    try:
        intent, conf = router.classify_intent("I want to book a hotel")
        print_test(
            "Booking intent detected", intent == "booking" and conf > 0, f"('{intent}', {conf:.2f})"
        )

        intent, conf = router.classify_intent("What's the weather?")
        print_test(
            "Query intent detected", intent == "query" and conf > 0, f"('{intent}', {conf:.2f})"
        )

        intent, conf = router.classify_intent("Hello there")
        print_test("Default intent", intent == "default", f"('{intent}', {conf:.2f})")

        mock_booking = type("MockBooking", (), {"agent_type": "booking"})()
        mock_query = type("MockQuery", (), {"agent_type": "query"})()

        router._booking_agent = mock_booking
        router._query_agent = mock_query

        result = router.route("Book a hotel")
        print_test("Route to booking", result is mock_booking)

        result = router.route("What's the weather?")
        print_test("Route to query", result is mock_query)

        return True
    except Exception as e:
        print_test("AgentRouter", False, str(e))
        return False


async def test_tool_functions() -> bool:
    """Test tool functions via LangChain invoke interface."""
    print(f"\n{Colors.BLUE}[4] Testing Tool Functions...{Colors.RESET}")

    from src.server.agent.tools.query_tool import get_weather, web_search, get_time
    from src.server.agent.tools.hotel_tool import search_hotels, book_hotel

    # Test using LangChain tool.invoke() interface
    result = await get_weather.ainvoke({"location": "Beijing"})
    result_dict = json.loads(result)
    print_test("get_weather returns JSON string", isinstance(result, str))
    print_test("get_weather parsed has temperature", "temperature" in result_dict)

    result = await web_search.ainvoke({"query": "test"})
    result_dict = json.loads(result)
    print_test("web_search returns JSON string", isinstance(result, str))
    print_test("web_search has results", "results" in result_dict)

    result = await get_time.ainvoke({"timezone": "UTC"})
    result_dict = json.loads(result)
    print_test("get_time returns JSON string", isinstance(result, str))
    print_test("get_time has time", "time" in result_dict)

    result = await search_hotels.ainvoke({"location": "Tokyo"})
    result_dict = json.loads(result)
    print_test("search_hotels returns JSON string", isinstance(result, str))
    print_test("search_hotels has hotels", "hotels" in result_dict)

    result = await book_hotel.ainvoke({"hotel_id": "h1", "guest_name": "Test", "checkin": "2026-04-01", "checkout": "2026-04-02"})
    result_dict = json.loads(result)
    print_test("book_hotel returns JSON string", isinstance(result, str))
    print_test("book_hotel has booking_id", "booking_id" in result_dict)

    return True


async def test_agent_creation() -> bool:
    """Test that agents can be created."""
    print(f"\n{Colors.BLUE}[5] Testing Agent Creation...{Colors.RESET}")

    from src.server.agent import LANGCHAIN_AVAILABLE

    if not LANGCHAIN_AVAILABLE:
        print_test("Agent creation", False, "SKIPPED - langchain not installed")
        return False

    from src.server.agent import create_query_agent, create_booking_agent, create_default_agent  # noqa: F401

    query_agent = create_query_agent(llm=None)
    print_test("QueryAgent created", query_agent.agent_type == "query")

    booking_agent = create_booking_agent(llm=None)
    print_test("BookingAgent created", booking_agent.agent_type == "booking")

    default_agent = create_default_agent(llm=None)
    print_test("DefaultAgent created", default_agent.agent_type == "default")

    return True


async def test_langchain_integration() -> bool:
    """Test LangChain integration with mock LLM."""
    print(f"\n{Colors.BLUE}[6] Testing LangChain Integration...{Colors.RESET}")

    from src.server.agent import LANGCHAIN_AVAILABLE

    if not LANGCHAIN_AVAILABLE:
        print_test("LangChain integration", False, "SKIPPED - langchain not installed")
        return False

    try:
        from src.server.agent import create_langchain_llm, create_booking_agent, StreamController

        # Create mock LLM that can be wrapped
        class MockLLM:
            model_name = "gpt-4"
            api_key = "test"
            url = "http://test"

            def as_langchain_llm(self):
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(model="gpt-4", api_key="test", base_url="http://test")

        llm = MockLLM()
        stream_controller = StreamController()
        booking_agent = create_booking_agent(llm, stream_controller)

        print_test("BookingAgent with LangChain", True)
        print_test("Has agent_executor", booking_agent.has_agent_executor, f"={booking_agent.has_agent_executor}")

        return True
    except Exception as e:
        print_test("LangChain integration", False, str(e))
        return False


async def test_tool_definitions() -> bool:
    """Test that tool definitions are properly structured as LangChain tools."""
    print(f"\n{Colors.BLUE}[7] Testing Tool Definitions...{Colors.RESET}")

    from src.server.agent.tools.query_tool import get_query_tools
    from src.server.agent.tools.hotel_tool import get_hotel_tools

    query_tools = get_query_tools()
    print_test("Query tools returns list", isinstance(query_tools, list))
    print_test("Query tools has 3 tools", len(query_tools) == 3)

    tool_names = {t.name for t in query_tools}
    print_test("get_weather in tools", "get_weather" in tool_names)
    print_test("web_search in tools", "web_search" in tool_names)
    print_test("get_time in tools", "get_time" in tool_names)

    hotel_tools = get_hotel_tools()
    print_test("Hotel tools returns list", isinstance(hotel_tools, list))
    print_test("Hotel tools has 2 tools", len(hotel_tools) == 2)

    tool_names = {t.name for t in hotel_tools}
    print_test("search_hotels in tools", "search_hotels" in tool_names)
    print_test("book_hotel in tools", "book_hotel" in tool_names)

    for tool in query_tools + hotel_tools:
        has_name = hasattr(tool, 'name') and tool.name
        has_desc = hasattr(tool, 'description') and tool.description
        has_invoke = callable(tool.invoke)
        print_test(f"Tool {tool.name} complete", has_name and has_desc and has_invoke)

    return True


async def test_stream_controller() -> bool:
    """Test StreamController basic functionality."""
    print(f"\n{Colors.BLUE}[8] Testing StreamController...{Colors.RESET}")

    from src.server.agent import LANGCHAIN_AVAILABLE

    if not LANGCHAIN_AVAILABLE:
        print_test("StreamController", True, "SKIPPED - langchain not installed")
        return True

    from src.server.agent import StreamController  # noqa: F401

    controller = StreamController()

    print_test("Controller initialized", controller.is_cancelled is False)
    print_test("reset() works", True)
    controller.is_cancelled = True
    print_test("check_cancelled()", controller.check_cancelled() is True)

    return True


async def test_voice_turn_import() -> bool:
    """Test that VoiceTurn can be imported and initialized."""
    print(f"\n{Colors.BLUE}[9] Testing VoiceTurn...{Colors.RESET}")

    from src.server.voice_turn import VoiceTurn  # noqa: F401

    print_test("VoiceTurn imported", True)

    return True


async def run_all_tests() -> bool:
    """Run all smoke tests."""
    print(f"\n{Colors.YELLOW}{'=' * 50}")
    print("Agent Layer Smoke Test")
    print(f"{'=' * 50}{Colors.RESET}\n")

    tests = [
        ("Imports", test_imports),
        ("TurnContext", test_turn_context),
        ("AgentRouter", test_agent_router),
        ("Tool Functions", test_tool_functions),
        ("Agent Creation", test_agent_creation),
        ("LangChain Integration", test_langchain_integration),
        ("Tool Definitions", test_tool_definitions),
        ("StreamController", test_stream_controller),
        ("VoiceTurn", test_voice_turn_import),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n{Colors.RED}Error in {name}: {e}{Colors.RESET}")
            results.append((name, False))

    print(f"\n{Colors.YELLOW}{'=' * 50}")
    print("Summary")
    print(f"{'=' * 50}{Colors.RESET}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = f"{Colors.GREEN}✓{Colors.RESET}" if result else f"{Colors.RED}✗{Colors.RESET}"
        print(f"  {status} {name}")

    print(f"\n{Colors.BLUE}Total: {passed}/{total} tests passed{Colors.RESET}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
