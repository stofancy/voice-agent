"""
Hotel booking tools for Voice Agent.

Provides tools for searching and booking hotels.
"""

from typing import Dict, Any
from datetime import datetime, timedelta


async def search_hotels(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search for available hotels.

    Args:
        input_data: Dict with optional 'location', 'checkin', 'checkout', 'guests'

    Returns:
        Dict with 'hotels' list
    """
    location = input_data.get("location", "any")
    checkin = input_data.get("checkin", (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))
    checkout = input_data.get("checkout", (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"))
    guests = input_data.get("guests", 1)

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

    return {
        "hotels": hotels,
        "checkin": checkin,
        "checkout": checkout,
        "guests": guests,
        "count": len(hotels),
    }


async def book_hotel(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Book a hotel room.

    Args:
        input_data: Dict with 'hotel_id', 'guest_name', 'checkin', 'checkout'

    Returns:
        Dict with 'booking_id', 'confirmation'
    """
    hotel_id = input_data.get("hotel_id")
    guest_name = input_data.get("guest_name", "Guest")
    checkin = input_data.get("checkin")
    checkout = input_data.get("checkout")

    booking_id = f"BK{int(datetime.now().timestamp())}"

    return {
        "booking_id": booking_id,
        "hotel_id": hotel_id,
        "guest_name": guest_name,
        "checkin": checkin,
        "checkout": checkout,
        "confirmation": f"Your booking {booking_id} is confirmed for {guest_name}.",
        "status": "confirmed",
    }


def get_hotel_tools():
    """Return list of hotel tools for LangChain agent."""
    return [
        {
            "name": "search_hotels",
            "description": "Search for available hotels. Input should include location, checkin date, checkout date, and number of guests.",
            "function": search_hotels,
        },
        {
            "name": "book_hotel",
            "description": "Book a hotel room. Input should include hotel_id, guest_name, checkin date, and checkout date.",
            "function": book_hotel,
        },
    ]
