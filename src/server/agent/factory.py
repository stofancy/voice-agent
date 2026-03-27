"""
Agent factory for creating configured agents.

Provides factory methods for creating agents with proper tool configurations.
"""


from .langchain_agent import LangChainAgent
from .tools.dummy_tool import get_dummy_tools
from .tools.query_tool import get_query_tools
from .tools.hotel_tool import get_hotel_tools


def create_query_agent(
    llm,
    stream_controller=None,
) -> LangChainAgent:
    """
    Create a query agent for handling information requests.

    Args:
        llm: LangChain-compatible LLM
        stream_controller: Optional stream controller for TTS

    Returns:
        Configured LangChainAgent instance
    """
    tools = get_query_tools()

    return LangChainAgent(
        agent_type="query",
        llm=llm,
        tools=tools,
        stream_controller=stream_controller,
        system_prompt="You are a helpful voice assistant that answers questions concisely.",
    )


def create_booking_agent(
    llm,
    stream_controller=None,
) -> LangChainAgent:
    """
    Create a booking agent for handling hotel/flight bookings.

    Args:
        llm: LangChain-compatible LLM
        stream_controller: Optional stream controller for TTS

    Returns:
        Configured LangChainAgent instance
    """
    tools = get_hotel_tools()

    return LangChainAgent(
        agent_type="booking",
        llm=llm,
        tools=tools,
        stream_controller=stream_controller,
        system_prompt="You are a voice assistant that helps users book hotels and flights. Be concise and confirm details before booking.",
    )


def create_default_agent(
    llm,
    stream_controller=None,
) -> LangChainAgent:
    """
    Create a default agent with general-purpose tools.

    Args:
        llm: LangChain-compatible LLM
        stream_controller: Optional stream controller for TTS

    Returns:
        Configured LangChainAgent instance
    """
    tools = get_dummy_tools()

    return LangChainAgent(
        agent_type="default",
        llm=llm,
        tools=tools,
        stream_controller=stream_controller,
        system_prompt="You are a helpful voice assistant. Keep responses concise for voice interaction.",
    )
