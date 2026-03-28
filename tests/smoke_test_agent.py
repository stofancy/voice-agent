#!/usr/bin/env python
"""
Smoke test for agent layer.

Tests the agent components directly without full voice pipeline.
"""

import asyncio
import sys

sys.path.insert(0, ".")


async def test_hotel_tools():
    """Test hotel tools directly."""
    print("🧪 Testing hotel tools...")

    import json
    from src.server.agent.tools.hotel_tool import search_hotels, book_hotel

    result_str = await search_hotels.ainvoke({"location": "Beijing"})
    result = json.loads(result_str)
    print(f"  ✓ search_hotels returned {result['count']} hotels")
    for h in result["hotels"]:
        print(f"    - {h['name']}: ${h['price']}/night")

    booking_str = await book_hotel.ainvoke(
        {
            "hotel_id": "h1",
            "guest_name": "Test User",
            "checkin": "2026-04-01",
            "checkout": "2026-04-02",
        }
    )
    booking = json.loads(booking_str)
    print(f"  ✓ book_hotel returned booking_id: {booking['booking_id']}")
    print(f"    Confirmation: {booking['confirmation']}")

    return True


async def main():
    """Run all smoke tests."""
    print("\n" + "=" * 50)
    print("🚀 Agent Layer Smoke Test")
    print("=" * 50 + "\n")

    # Test imports
    print("─" * 40)
    print("🧪 Testing imports...")
    from src.server.agent import (
        BaseAgent,
        AgentEvent,
        LANGCHAIN_AVAILABLE,
    )

    print(f"  ✓ All imports successful")
    print(f"  ℹ️  LangChain available: {LANGCHAIN_AVAILABLE}")

    # Test events
    print("\n─" * 40)
    print("🧪 Testing event classes...")
    event = AgentEvent("test", {"key": "value"})
    assert event.event_type == "test"
    assert event.data == {"key": "value"}
    print(f"  ✓ AgentEvent works correctly")

    # Test progress messages
    print("\n─" * 40)
    print("🧪 Testing tool progress messages...")
    from src.server.agent.langchain_agent import TOOL_PROGRESS_MESSAGES

    print("  ✓ Tool progress messages:")
    for key, msg in TOOL_PROGRESS_MESSAGES.items():
        print(f"    - {key}: {msg}")

    # Test hotel tools
    print("\n─" * 40)
    result = await test_hotel_tools()

    # Test booking agent
    print("\n─" * 40)
    print("🧪 Testing BookingAgent...")
    from src.server.agent.booking_agent import BookingAgent

    agent = BookingAgent(llm=None)
    assert agent.agent_type == "booking"
    assert len(agent._tools) == 2
    print(f"  ✓ BookingAgent created with {len(agent._tools)} tools:")
    for tool in agent._tools:
        print(f"    - {tool.name}")

    print(f"\n{'=' * 50}")
    print(f"📊 All tests PASSED")
    print("=" * 50 + "\n")

    return True


if __name__ == "__main__":
    asyncio.run(main())
