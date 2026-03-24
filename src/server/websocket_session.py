"""
WebSocket session management.

Encapsulates per-connection state and provides cancel/listen helpers.
"""

import asyncio
from typing import Optional

from fastapi import WebSocket

from .audio import AudioBuffer
from .connection import ConnectionState, ConnectionStateMachine, WebSocketConnection
from .turn_context import TurnContext


class WebSocketSession:
    """
    Manages state for a single WebSocket connection.

    Encapsulates:
    - connection_state: ConnectionStateMachine
    - audio_buffer: AudioBuffer
    - turn_context: TurnContext
    - response_task: Optional[asyncio.Task]
    """

    def __init__(self, websocket: WebSocket):
        self._ws = websocket
        self.connection_state = ConnectionStateMachine()
        self.audio_buffer = AudioBuffer()
        self.turn_context = TurnContext()
        self.response_task: Optional[asyncio.Task] = None

    @property
    def websocket(self) -> WebSocket:
        return self._ws

    @property
    def is_listening(self) -> bool:
        return self.connection_state.is_listening()

    @property
    def is_idle(self) -> bool:
        return self.connection_state.is_idle()

    async def send_listening_stopped(self) -> None:
        """Send listening_stopped and transition to IDLE."""
        await self._ws.send_json({"type": "listening_stopped"})
        self.connection_state.transition_to(ConnectionState.IDLE)

    async def cancel_response(self, send_interrupt_event: bool) -> None:
        """Cancel current response task."""
        self.turn_context.cancel()
        if self.response_task and not self.response_task.done():
            self.response_task.cancel()
            try:
                await self.response_task
            except asyncio.CancelledError:
                pass
        self.response_task = None
        if send_interrupt_event:
            await self._ws.send_json({"type": "interrupt_complete"})

    def start_response(self, task: asyncio.Task) -> None:
        """Start a new response task."""
        self.response_task = task
