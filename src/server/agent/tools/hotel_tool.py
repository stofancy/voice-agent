"""
Hotel booking tools for Voice Agent.

Provides tools for searching and booking hotels.
"""

import json
from datetime import datetime, timedelta

from langchain_core.tools import tool


@tool
async def search_hotels(
    location: str = "any",
    checkin: str = None,
    checkout: str = None,
    guests: int = 1,
) -> str:
    """
    Search for available hotels.

    Args:
        location: City or area to search for hotels
        checkin: Check-in date in YYYY-MM-DD format (defaults to tomorrow)
        checkout: Check-out date in YYYY-MM-DD format (defaults to day after tomorrow)
        guests: Number of guests (defaults to 1)

    Returns:
        JSON string with list of available hotels
    """
    if checkin is None:
        checkin = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if checkout is None:
        checkout = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

    hotels = [
        {
            "id": "h1",
            "name": "Grand Hotel",
            "location": location or "Downtown",
            "price": 150.00,
            "rating": 4.5,
            "available": True,
        },
        {
            "id": "h2",
            "name": "Seaside Resort",
            "location": location or "Beach Area",
            "price": 220.00,
            "rating": 4.8,
            "available": True,
        },
    ]

    result = {
        "hotels": hotels,
        "checkin": checkin,
        "checkout": checkout,
        "guests": guests,
        "count": len(hotels),
    }
    return json.dumps(result)


@tool
async def book_hotel(
    hotel_id: str,
    guest_name: str,
    checkin: str = None,
    checkout: str = None,
) -> str:
    """
    Book a hotel room.

    Args:
        hotel_id: ID of the hotel to book
        guest_name: Name of the guest for the booking
        checkin: Check-in date in YYYY-MM-DD format
        checkout: Check-out date in YYYY-MM-DD format

    Returns:
        JSON string with booking confirmation details
    """
    booking_id = f"BK{int(datetime.now().timestamp())}"

    result = {
        "booking_id": booking_id,
        "hotel_id": hotel_id,
        "guest_name": guest_name,
        "checkin": checkin,
        "checkout": checkout,
        "confirmation": f"Your booking {booking_id} is confirmed for {guest_name}.",
        "status": "confirmed",
    }
    return json.dumps(result)


def get_hotel_tools():
    """Return list of hotel tools for LangChain agent."""
    return [search_hotels, book_hotel]
