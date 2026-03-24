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

try:
    from .stream_controller import StreamController
    from .llm_factory import LangChainLLMWrapper, create_langchain_llm

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    StreamController = None
    LangChainLLMWrapper = None
    create_langchain_llm = None

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
    "LANGCHAIN_AVAILABLE",
]
