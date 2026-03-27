"""
Dummy tool for testing non-blocking tool calls.
"""

from langchain_core.tools import tool


@tool
async def echo_tool(message: str) -> str:
    """
    Echoes back the input message. Use for testing.

    Args:
        message: The message to echo back

    Returns:
        A confirmation with the echoed message
    """
    import asyncio
    await asyncio.sleep(0.1)  # Simulate light processing
    return f'{{"echo": "{message}", "status": "completed"}}'


def get_dummy_tools():
    """Return list of dummy tools for LangChain agent."""
    return [echo_tool]


# Direct implementation for testing (same logic as @tool version)
async def echo_tool_impl(message: str) -> dict:
    """Direct implementation of echo tool for testing."""
    import asyncio
    await asyncio.sleep(0.1)
    return {"echo": message, "status": "completed"}
