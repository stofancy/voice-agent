"""
Typed WebSocket message definitions.

Provides message classes for all WebSocket protocol messages,
replacing raw dict parsing with type-safe objects.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any


class MessageType(str, Enum):
    """All possible WebSocket message types."""
    START_LISTENING = "start_listening"
    STOP_LISTENING = "stop_listening"
    AUDIO = "audio"
    INTERRUPT = "interrupt"
    PING = "ping"
    PERF_REPORT = "perf_report"
    UNKNOWN = "unknown"


@dataclass
class WSMessage:
    """Base WebSocket message."""
    type: MessageType
    data: dict[str, Any]


@dataclass
class StartListeningMessage(WSMessage):
    """start_listening message - begins recording."""
    def __init__(self):
        super().__init__(type=MessageType.START_LISTENING, data={})


@dataclass
class StopListeningMessage(WSMessage):
    """stop_listening message - ends recording and triggers STT."""
    def __init__(self):
        super().__init__(type=MessageType.STOP_LISTENING, data={})


@dataclass
class AudioMessage(WSMessage):
    """audio message - contains base64 encoded audio data."""
    audio_data: bytes

    @classmethod
    def from_dict(cls, data: dict) -> "AudioMessage":
        """Create from dict with 'data' key containing base64 string."""
        import base64
        audio_b64 = data.get("data", "")
        audio_bytes = base64.b64decode(audio_b64)
        return cls(type=MessageType.AUDIO, data=data, audio_data=audio_bytes)


@dataclass
class InterruptMessage(WSMessage):
    """interrupt message - cancels current response."""
    def __init__(self):
        super().__init__(type=MessageType.INTERRUPT, data={})


@dataclass
class PingMessage(WSMessage):
    """ping message - heartbeat."""
    def __init__(self):
        super().__init__(type=MessageType.PING, data={})


@dataclass
class PerfReportMessage(WSMessage):
    """perf_report message - client-side performance metrics."""
    metrics: dict

    @classmethod
    def from_dict(cls, data: dict) -> "PerfReportMessage":
        """Create from dict with 'metrics' key."""
        return cls(type=MessageType.PERF_REPORT, data=data, metrics=data.get("metrics", {}))


@dataclass
class UnknownMessage(WSMessage):
    """Unknown message type - fallback."""
    raw_type: str

    @classmethod
    def from_dict(cls, raw_type: str, data: dict) -> "UnknownMessage":
        return cls(raw_type=raw_type, type=MessageType.UNKNOWN, data=data)


def parse_message(raw: str) -> WSMessage:
    """
    Parse a raw JSON string into a typed WSMessage.

    Args:
        raw: JSON string from WebSocket

    Returns:
        Typed message subclass instance
    """
    import json
    msg = json.loads(raw)
    msg_type = msg.get("type", "")
    msg_data = msg.get("data", {})

    match msg_type:
        case "start_listening":
            return StartListeningMessage()
        case "stop_listening":
            return StopListeningMessage()
        case "audio":
            return AudioMessage.from_dict(msg)
        case "interrupt":
            return InterruptMessage()
        case "ping":
            return PingMessage()
        case "perf_report":
            return PerfReportMessage.from_dict(msg)
        case _:
            return UnknownMessage.from_dict(msg_type, msg_data)
