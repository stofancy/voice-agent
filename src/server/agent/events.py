"""
Event definitions for agent layer.

All events emitted by the agent system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ToolStatus(Enum):
    """Tool execution status."""

    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ToolStartEvent:
    """Event emitted when a tool starts execution."""

    tool_name: str
    tool_input: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "tool_start",
            "tool": self.tool_name,
            "input": self.tool_input,
        }


@dataclass
class ToolProgressEvent:
    """Event emitted during tool execution for progress updates."""

    tool_name: str
    status: str
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "tool_progress",
            "tool": self.tool_name,
            "status": self.status,
            "message": self.message,
        }


@dataclass
class ToolCompleteEvent:
    """Event emitted when a tool completes execution."""

    tool_name: str
    tool_output: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "tool_complete",
            "tool": self.tool_name,
            "output": self.tool_output,
        }


@dataclass
class ToolErrorEvent:
    """Event emitted when a tool fails."""

    tool_name: str
    error: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "tool_error",
            "tool": self.tool_name,
            "error": self.error,
        }


@dataclass
class StreamChunkEvent:
    """Event emitted for each text chunk in the stream."""

    text: str
    is_final: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "stream_chunk",
            "text": self.text,
            "is_final": self.is_final,
        }


@dataclass
class AgentStartEvent:
    """Event emitted when agent starts processing."""

    agent_type: str
    input_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "agent_start",
            "agent_type": self.agent_type,
            "input": self.input_text,
        }


@dataclass
class AgentCompleteEvent:
    """Event emitted when agent finishes processing."""

    agent_type: str
    full_response: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "agent_complete",
            "agent_type": self.agent_type,
            "response": self.full_response,
        }


# Union type for all agent events
AgentEvent = (
    ToolStartEvent
    | ToolProgressEvent
    | ToolCompleteEvent
    | ToolErrorEvent
    | StreamChunkEvent
    | AgentStartEvent
    | AgentCompleteEvent
)
