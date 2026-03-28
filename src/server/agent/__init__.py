"""
Self-managed agent layer for Voice Agent.

Replaces OpenClaw dependency with LangChain Agents for full streaming control.
"""

from .base import BaseAgent, AgentEvent
from .events import (
    ToolStatus,
    ToolStartEvent,
    ToolProgressEvent,
    ToolCompleteEvent,
    ToolErrorEvent,
    StreamChunkEvent,
    AgentStartEvent,
    AgentCompleteEvent,
)
from .langchain_agent import LangChainAgent
from .router import AgentRouter
from .query_agent import QueryAgent
from .booking_agent import BookingAgent

try:
    from .stream_controller import StreamController
    from .llm_factory import LangChainLLMWrapper, create_langchain_llm
    from .factory import (
        create_query_agent,
        create_booking_agent,
        create_default_agent,
        _create_react_agent_executor,
    )
    from .agent_streaming_synthesis import AgentStreamingSynthesis, AgentSynthesisConfig

    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    StreamController = None
    LangChainLLMWrapper = None
    create_langchain_llm = None
    create_query_agent = None
    create_booking_agent = None
    create_default_agent = None
    _create_react_agent_executor = None
    LangChainAgent = None
    AgentStreamingSynthesis = None
    AgentSynthesisConfig = None

__all__ = [
    "BaseAgent",
    "AgentEvent",
    "ToolStatus",
    "ToolStartEvent",
    "ToolProgressEvent",
    "ToolCompleteEvent",
    "ToolErrorEvent",
    "StreamChunkEvent",
    "AgentStartEvent",
    "AgentCompleteEvent",
    "StreamController",
    "LangChainLLMWrapper",
    "create_langchain_llm",
    "LangChainAgent",
    "create_query_agent",
    "create_booking_agent",
    "create_default_agent",
    "AgentStreamingSynthesis",
    "AgentSynthesisConfig",
    "AgentRouter",
    "QueryAgent",
    "BookingAgent",
    "LANGCHAIN_AVAILABLE",
]
