"""
Dummy tool for testing non-blocking tool calls.
"""

from typing import Dict, Any


async def echo_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple echo tool for testing.

    Args:
        input_data: Dictionary with 'message' key

    Returns:
        Dictionary with 'echo' key containing the echoed message
    """
    message = input_data.get("message", "")
    return {"echo": message, "status": "completed"}


def get_dummy_tools():
    """Return list of dummy tools for LangChain agent."""
    return [
        {
            "name": "echo",
            "description": "Echoes back the input message. Use for testing.",
            "function": echo_tool,
        }
    ]
