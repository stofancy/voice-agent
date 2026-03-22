"""
Connection state machine and WebSocket wrapper.

Provides:
- ConnectionState: Enum for connection states
- ConnectionStateMachine: Manages state transitions
- WebSocketConnection: Wraps WebSocket with typed send methods
"""

from enum import Enum
from typing import Optional, Any

from fastapi import WebSocket


class ConnectionState(str, Enum):
    """Connection states for the voice turn state machine."""
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"


class ConnectionStateMachine:
    """Manages connection state transitions."""

    def __init__(self):
        self._state: ConnectionState = ConnectionState.IDLE

    @property
    def state(self) -> ConnectionState:
        """Get current state."""
        return self._state

    def transition_to(self, new_state: ConnectionState) -> None:
        """Transition to a new state."""
        self._state = new_state

    def is_idle(self) -> bool:
        return self._state == ConnectionState.IDLE

    def is_listening(self) -> bool:
        return self._state == ConnectionState.LISTENING

    def is_processing(self) -> bool:
        return self._state == ConnectionState.PROCESSING

    def is_speaking(self) -> bool:
        return self._state == ConnectionState.SPEAKING


class WebSocketConnection:
    """Wraps WebSocket with typed send methods and message building."""

    def __init__(self, websocket: WebSocket):
        self._ws = websocket

    async def accept(self) -> None:
        """Accept the WebSocket connection."""
        await self._ws.accept()

    async def close(self, code: int = 1000) -> None:
        """Close the WebSocket connection."""
        await self._ws.close(code=code)

    async def receive_text(self) -> str:
        """Receive raw text message from WebSocket."""
        return await self._ws.receive_text()

    async def send_json(self, data: dict) -> None:
        """Send JSON message."""
        await self._ws.send_json(data)

    async def send_listening_started(self) -> None:
        """Send listening_started message."""
        await self.send_json({"type": "listening_started"})

    async def send_listening_stopped(self) -> None:
        """Send listening_stopped message."""
        await self.send_json({"type": "listening_stopped"})

    async def send_transcript(self, text: str) -> None:
        """Send transcript message."""
        await self.send_json({"type": "transcript", "text": text, "final": True})

    async def send_tts_start(self) -> None:
        """Send tts_start message."""
        await self.send_json({"type": "tts_start"})

    async def send_audio_chunk(self, data: bytes, sample_rate: int) -> None:
        """Send audio_chunk message with base64 encoded audio."""
        import base64
        audio_b64 = base64.b64encode(data).decode()
        await self.send_json({"type": "audio_chunk", "data": audio_b64, "sample_rate": sample_rate})

    async def send_tts_end(self, interrupted: bool = False) -> None:
        """Send tts_end message."""
        await self.send_json({"type": "tts_end", "interrupted": interrupted})

    async def send_response_complete(self, text: str) -> None:
        """Send response_complete message."""
        await self.send_json({"type": "response_complete", "text": text})

    async def send_subtitle_chunk(self, text: str) -> None:
        """Send subtitle_chunk message."""
        await self.send_json({"type": "subtitle_chunk", "text": text})

    async def send_vad_status(self, speech_detected: bool) -> None:
        """Send vad_status message."""
        await self.send_json({"type": "vad_status", "speech_detected": speech_detected})

    async def send_interrupt_ack(self) -> None:
        """Send interrupt_ack message."""
        await self.send_json({"type": "interrupt_ack"})

    async def send_interrupt_complete(self) -> None:
        """Send interrupt_complete message."""
        await self.send_json({"type": "interrupt_complete"})

    async def send_pong(self) -> None:
        """Send pong message."""
        await self.send_json({"type": "pong"})

    @property
    def client_info(self) -> str:
        """Get client info for logging."""
        return f"WebSocket"
