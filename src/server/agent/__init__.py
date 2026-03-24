"""
Self-managed agent layer for Voice Agent.

Replaces OpenClaw dependency with LangChain Agents for full streaming control.
"""

from .base import BaseAgent
from .events import AgentEvent, ToolEvent, ToolStatus
from .stream_controller import StreamController

__all__ = [
    "BaseAgent",
    "AgentEvent",
    "ToolEvent",
    "ToolStatus",
    "StreamController",
]
