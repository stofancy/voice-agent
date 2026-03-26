"""
Query tools for Voice Agent.

Provides tools for information queries like weather and web search.
"""

from typing import Dict, Any
from datetime import datetime


async def get_weather(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get weather information for a location.

    Args:
        input_data: Dict with 'location' key

    Returns:
        Dict with weather information
    """
    location = input_data.get("location", "unknown")

    conditions = ["sunny", "cloudy", "rainy", "partly cloudy", "clear"]
    import random

    condition = random.choice(conditions)
    temp = random.randint(15, 30)

    return {
        "location": location,
        "temperature": temp,
        "condition": condition,
        "humidity": random.randint(40, 80),
        "wind_speed": random.randint(5, 20),
        "forecast": f"The weather in {location} is {condition} with a temperature of {temp} degrees Celsius.",
    }


async def web_search(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search the web for information.

    Args:
        input_data: Dict with 'query' key

    Returns:
        Dict with search results
    """
    query = input_data.get("query", "")

    return {
        "query": query,
        "results": [
            {
                "title": f"Result 1 for {query}",
                "url": f"https://example.com/result1?q={query}",
                "snippet": f"This is a relevant result about {query}...",
            },
            {
                "title": f"Result 2 for {query}",
                "url": f"https://example.com/result2?q={query}",
                "snippet": f"Another relevant result about {query}...",
            },
        ],
        "count": 2,
    }


async def get_time(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current time for a location.

    Args:
        input_data: Dict with optional 'timezone' key

    Returns:
        Dict with time information
    """
    timezone = input_data.get("timezone", "UTC")
    now = datetime.now()

    return {
        "timezone": timezone,
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "formatted": f"The current time is {now.strftime('%H:%M:%S')} on {now.strftime('%Y-%m-%d')}.",
    }


def get_query_tools():
    """Return list of query tools for LangChain agent."""
    return [
        {
            "name": "get_weather",
            "description": "Get weather information for a location. Input should include 'location'.",
            "function": get_weather,
        },
        {
            "name": "web_search",
            "description": "Search the web for information. Input should include 'query'.",
            "function": web_search,
        },
        {
            "name": "get_time",
            "description": "Get current time for a timezone. Input should include optional 'timezone' (default UTC).",
            "function": get_time,
        },
    ]
