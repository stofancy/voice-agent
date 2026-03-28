#!/usr/bin/env python3
"""
Demo script for browser booking system.

This demonstrates how to use the BrowserController and stage tools
for hotel booking automation.

Usage:
    python -m src.server.browser.demo
"""

import asyncio
import json

from loguru import logger

from .browser_controller import BrowserController, BrowserControllerConfig
from .stages import (
    BookHotelSearchTool,
    BookHotelSelectHotelTool,
    BookHotelNavigatePropertyTool,
    BookHotelSelectRoomTool,
    BookHotelConfirmSelectionTool,
    BookHotelFillGuestTool,
    BookHotelFinalizeTool,
    TurnContext,
)


async def demo_basic_navigation():
    """Demo basic browser navigation."""
    print("\n=== Demo: Basic Browser Navigation ===\n")

    config = BrowserControllerConfig(
        chrome_url="http://127.0.0.1:9222",
        screenshot_dir="/tmp/openclaw_screenshots",
    )

    bc = BrowserController(config)

    try:
        # Connect (starts MCP process)
        await bc.connect()

        # List open pages
        pages = await bc.list_pages()
        print(f"Open pages: {len(pages)}")
        for page in pages:
            print(f"  - [{page.page_id}] {page.title}: {page.url}")

        # Navigate to Booking.com
        print("\nNavigating to Booking.com...")
        await bc.navigate("https://www.booking.com")

        # Take screenshot
        screenshot = await bc.take_screenshot()
        print(f"Screenshot saved: {len(screenshot.data)} bytes")

        # Check login status
        login_status = await bc.check_login_status()
        print(f"Login status: {login_status}")

    finally:
        await bc.disconnect()


async def demo_search_flow():
    """Demo hotel search flow."""
    print("\n=== Demo: Hotel Search Flow ===\n")

    config = BrowserControllerConfig()
    bc = BrowserController(config)

    # Create turn context with search parameters
    context = {
        "location": "Tokyo",
        "checkin": "2026-04-01",
        "checkout": "2026-04-05",
        "guests": 2,
        "rooms": 1,
    }

    try:
        await bc.connect()

        # Stage 1: Search
        search_tool = BookHotelSearchTool()
        result = await search_tool.execute(bc, context)
        print(f"Search result: {json.dumps(result.to_dict(), indent=2, ensure_ascii=False)}")

        if result.action.value == "continue":
            # Stage 2: Select Hotel
            select_tool = BookHotelSelectHotelTool()
            result = await select_tool.execute(bc, context)
            print(f"\nHotels found: {result.data.get('count', 0)}")

            for opt in result.options[:3]:
                print(f"  {opt['index']}. {opt['display']}")

            # Simulate user selecting first hotel
            if result.options:
                context["selected_hotel"] = result.options[0]["details"]
                print(f"\nSelected: {context['selected_hotel']['name']}")

                # Stage 3: Navigate to property
                nav_tool = BookHotelNavigatePropertyTool()
                result = await nav_tool.execute(bc, context)
                print(f"\nProperty page: {result.data.get('property_url')}")

    finally:
        await bc.disconnect()


async def demo_full_booking_flow():
    """Demo full booking flow with mock data."""
    print("\n=== Demo: Full Booking Flow ===\n")

    # Create mock context simulating a completed booking flow
    context = {
        "location": "Tokyo",
        "checkin": "2026-04-01",
        "checkout": "2026-04-05",
        "guests": 2,
        "rooms": 1,
        "selected_hotel": {
            "name": "Millennium Mitsui Garden Hotel Tokyo - Ginza",
            "price": "CNY 12,123",
            "score": "9.7",
            "location": "Chuo Ward, Tokyo (Ginza)",
            "url": "https://www.booking.com/hotel/jp/millennium-mitsui-garden.html",
        },
        "selected_room": {
            "name": "Standard Double Room",
            "price": "CNY 12,123",
            "max_guests": 2,
            "bed_type": "1 double bed",
        },
        "guest_name": "John Doe",
        "guest_email": "john.doe@example.com",
    }

    # Stage 5: Confirm Selection
    confirm_tool = BookHotelConfirmSelectionTool()
    result = await confirm_tool.execute(None, context)
    print(f"Confirmation:\n{result.message}\n")

    # Stage 6: Fill Guest
    guest_tool = BookHotelFillGuestTool()
    result = await guest_tool.execute(None, context)
    print(f"Guest info: {result.data}\n")

    # Stage 7: Finalize
    finalize_tool = BookHotelFinalizeTool()
    print("Finalize would click Book button and reach payment page")
    print("(Skipped in demo - requires real browser interaction)")


async def main():
    """Run demos."""
    logger.info("Starting browser booking demo")

    # Note: These demos require Chrome with remote debugging enabled
    # Start Chrome with: /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

    try:
        # Demo full booking flow (mock data, no browser needed)
        await demo_full_booking_flow()

        # Demo with real browser (requires Chrome running)
        # await demo_basic_navigation()
        # await demo_search_flow()

    except Exception as e:
        print(f"Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
