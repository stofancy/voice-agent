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
from .stream_controller import StreamController
from .llm_factory import LangChainLLMWrapper, create_langchain_llm

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
]
