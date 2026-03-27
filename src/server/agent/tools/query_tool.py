"""
Query tools for Voice Agent.

Provides tools for information queries like weather and web search.
"""

import json
import random
from datetime import datetime

from langchain_core.tools import tool


@tool
async def get_weather(location: str) -> str:
    """
    Get weather information for a location.

    Args:
        location: City name to get weather for

    Returns:
        JSON string with weather information including temperature and conditions
    """
    conditions = ["sunny", "cloudy", "rainy", "partly cloudy", "clear"]
    condition = random.choice(conditions)
    temp = random.randint(15, 30)

    result = {
        "location": location,
        "temperature": temp,
        "condition": condition,
        "humidity": random.randint(40, 80),
        "wind_speed": random.randint(5, 20),
        "forecast": f"The weather in {location} is {condition} with a temperature of {temp} degrees Celsius.",
    }
    return json.dumps(result)


@tool
async def web_search(query: str) -> str:
    """
    Search the web for information.

    Args:
        query: Search query to look up

    Returns:
        JSON string with search results
    """
    results = [
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
    ]

    result = {
        "query": query,
        "results": results,
        "count": len(results),
    }
    return json.dumps(result)


@tool
async def get_time(timezone: str = "UTC") -> str:
    """
    Get current time for a timezone.

    Args:
        timezone: Timezone name (e.g., 'UTC', 'America/New_York'). Defaults to UTC.

    Returns:
        JSON string with current time and date information
    """
    now = datetime.now()

    result = {
        "timezone": timezone,
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "formatted": f"The current time is {now.strftime('%H:%M:%S')} on {now.strftime('%Y-%m-%d')}.",
    }
    return json.dumps(result)


def get_query_tools():
    """Return list of query tools for LangChain agent."""
    return [get_weather, web_search, get_time]
