"""
Agent factory for creating configured agents.

Provides factory methods for creating agents with proper tool configurations.
"""

from typing import Any, List, Optional

from .langchain_agent import LangChainAgent
from .tools.dummy_tool import get_dummy_tools
from .tools.query_tool import get_query_tools
from .tools.hotel_tool import get_hotel_tools


def _create_react_agent_executor(
    llm: Any,
    tools: List[Any],
    system_prompt: str,
) -> Any:
    """
    Create a LangChain ReAct agent executor.

    Args:
        llm: LangChain ChatOpenAI instance
        tools: List of LangChain tools
        system_prompt: System prompt for the agent

    Returns:
        AgentExecutor ready for streaming
    """
    # Import here to avoid top-level import issues when langchain not available
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    # Create ReAct agent prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # Create the agent
    agent = create_react_agent(llm, tools, prompt=prompt)

    # Create executor
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        stream_rdry_output=True,
    )

    return executor


def create_query_agent(
    llm: Any,
    stream_controller=None,
) -> LangChainAgent:
    """
    Create a query agent for handling information requests.

    Args:
        llm: LangChain-compatible LLM (ChatOpenAI)
        stream_controller: Optional stream controller for TTS

    Returns:
        Configured LangChainAgent instance with ReAct agent executor
    """
    tools = get_query_tools()
    system_prompt = "You are a helpful voice assistant that answers questions concisely."

    # Create agent executor if llm is ChatOpenAI-like
    agent_executor = None
    if llm is not None and hasattr(llm, "model_name"):
        # llm is a LangChainLLMWrapper - get the underlying ChatOpenAI
        try:
            chat_llm = llm.as_langchain_llm()
            agent_executor = _create_react_agent_executor(chat_llm, tools, system_prompt)
        except Exception:
            pass

    return LangChainAgent(
        agent_type="query",
        llm=llm,
        tools=tools,
        stream_controller=stream_controller,
        system_prompt=system_prompt,
        agent_executor=agent_executor,
    )


def create_booking_agent(
    llm: Any,
    stream_controller=None,
) -> LangChainAgent:
    """
    Create a booking agent for handling hotel/flight bookings.

    Args:
        llm: LangChain-compatible LLM (ChatOpenAI)
        stream_controller: Optional stream controller for TTS

    Returns:
        Configured LangChainAgent instance with ReAct agent executor
    """
    tools = get_hotel_tools()
    system_prompt = """You are a voice booking assistant. Help users book hotels and flights.

For hotels:
- Ask for location, dates, and guest count
- Use search_hotels to find options
- Use book_hotel to confirm booking
- Confirm all details before booking

Keep responses concise for voice interaction. Confirm booking reference at the end."""

    # Create agent executor if llm is ChatOpenAI-like
    agent_executor = None
    if llm is not None and hasattr(llm, "model_name"):
        # llm is a LangChainLLMWrapper - get the underlying ChatOpenAI
        try:
            chat_llm = llm.as_langchain_llm()
            agent_executor = _create_react_agent_executor(chat_llm, tools, system_prompt)
        except Exception:
            pass

    return LangChainAgent(
        agent_type="booking",
        llm=llm,
        tools=tools,
        stream_controller=stream_controller,
        system_prompt=system_prompt,
        agent_executor=agent_executor,
    )


def create_default_agent(
    llm: Any,
    stream_controller=None,
) -> LangChainAgent:
    """
    Create a default agent with general-purpose tools.

    Args:
        llm: LangChain-compatible LLM (ChatOpenAI)
        stream_controller: Optional stream controller for TTS

    Returns:
        Configured LangChainAgent instance with ReAct agent executor
    """
    tools = get_dummy_tools()
    system_prompt = "You are a helpful voice assistant. Keep responses concise for voice interaction."

    # Create agent executor if llm is ChatOpenAI-like
    agent_executor = None
    if llm is not None and hasattr(llm, "model_name"):
        # llm is a LangChainLLMWrapper - get the underlying ChatOpenAI
        try:
            chat_llm = llm.as_langchain_llm()
            agent_executor = _create_react_agent_executor(chat_llm, tools, system_prompt)
        except Exception:
            pass

    return LangChainAgent(
        agent_type="default",
        llm=llm,
        tools=tools,
        stream_controller=stream_controller,
        system_prompt=system_prompt,
        agent_executor=agent_executor,
    )
