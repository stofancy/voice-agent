"""
Voice turn orchestration.

Handles a complete voice turn: STT → StreamingSynthesis → WebSocket messages.
"""

import asyncio
import base64
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
from loguru import logger

from .connection import ConnectionState, ConnectionStateMachine, WebSocketConnection


@dataclass
class TurnMetrics:
    """Metrics collected during a voice turn."""
    stt_ms: Optional[float] = None
    llm_ttft_ms: Optional[float] = None
    llm_gen_ms: Optional[float] = None
    tts_ttfa_ms: Optional[float] = None
    tts_total_ms: Optional[float] = None
    audio_chunks_sent: int = 0


class VoiceTurn:
    """
    Orchestrates a complete voice turn.

    Handles:
    - STT transcription
    - LLM + TTS streaming (via StreamingSynthesis)
    - WebSocket message state machine

    Usage:
        turn = VoiceTurn(
            stt=stt,
            synthesis=streaming_synthesis,
            websocket=ws,
            config=turn_config,
        )
        result = await turn.execute(audio_data)
    """

    def __init__(
        self,
        stt,  # BaseSTT
        synthesis,  # StreamingSynthesis
        websocket: WebSocketConnection,
        config,  # TurnConfig or similar
    ):
        self._stt = stt
        self._synthesis = synthesis
        self._ws = websocket
        self._config = config
        self._state = ConnectionStateMachine()

    async def execute(self, audio_data: np.ndarray) -> tuple[str, TurnMetrics]:
        """
        Execute a complete voice turn.

        Args:
            audio_data: Audio numpy array from STT

        Returns:
            Tuple of (full_response, metrics)
        """
        metrics = TurnMetrics()
        t_start = time.perf_counter()

        # STT stage
        self._state.transition_to(ConnectionState.PROCESSING)
        transcript, success = await self._stt.transcribe(audio_data)

        t_stt_end = time.perf_counter()
        metrics.stt_ms = (t_stt_end - t_start) * 1000

        await self._ws.send_transcript(transcript)
        logger.info(f"🎤 Transcript: {transcript}")

        if not transcript.strip() or not success:
            self._state.transition_to(ConnectionState.IDLE)
            await self._ws.send_listening_stopped()
            return "", metrics

        # LLM + TTS streaming
        self._state.transition_to(ConnectionState.SPEAKING)
        await self._ws.send_tts_start()

        result = await self._synthesis.run(transcript)

        # Update metrics from synthesis result
        metrics.llm_ttft_ms = result.metrics.llm_ttft_ms
        metrics.llm_gen_ms = result.metrics.llm_gen_ms
        metrics.tts_ttfa_ms = result.metrics.tts_ttfa_ms
        metrics.tts_total_ms = result.metrics.tts_total_ms
        metrics.audio_chunks_sent = result.metrics.audio_chunks_sent

        await self._ws.send_tts_end(interrupted=False)
        await self._ws.send_response_complete(result.full_response)
        self._state.transition_to(ConnectionState.IDLE)
        await self._ws.send_listening_stopped()

        return result.full_response, metrics

    async def handle_interrupt(self):
        """Handle an interrupt request."""
        self._state.transition_to(ConnectionState.IDLE)
        await self._ws.send_interrupt_ack()
