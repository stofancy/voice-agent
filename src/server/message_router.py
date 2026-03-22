"""
Message handler functions for WebSocket message handling.
"""

import asyncio
from typing import TYPE_CHECKING, Awaitable, Callable, Optional

from .connection import ConnectionState, ConnectionStateMachine, WebSocketConnection
from .messages import WSMessage, AudioMessage, PerfReportMessage
from .websocket_session import WebSocketSession

if TYPE_CHECKING:
    from fastapi import WebSocket
    from .llm import BaseLLM
    from .tts import BaseTTS
    from .stt import BaseSTT
    from .vad import VoiceActivityDetector
    from .streaming_synthesis import SynthesisConfig


async def handle_start_listening(
    session: WebSocketSession,
) -> None:
    """Handle start_listening: clears buffer and starts recording."""
    await session.cancel_response(send_interrupt_event=False)
    session.audio_buffer.clear()
    session.connection_state.transition_to(ConnectionState.LISTENING)
    await session.websocket.send_json({"type": "listening_started"})


async def handle_stop_listening(
    session: WebSocketSession,
    stt: "BaseSTT",
    backend: "BaseLLM",
    tts: "BaseTTS",
    TTS_DATA_BUFFER_SIZE: int,
    TTS_TIME_BUFFER_SECONDS: float,
    TTS_SAMPLE_RATE: int,
    SUBTITLE_STREAMING: bool,
) -> Optional[asyncio.Task]:
    """Handle stop_listening: transcribes audio and starts response."""
    from .streaming_synthesis import SynthesisConfig
    from .voice_turn import VoiceTurn

    if not session.is_listening:
        await session.send_listening_stopped()
        return None

    if session.audio_buffer.is_empty():
        await session.send_listening_stopped()
        return None

    audio_data = session.audio_buffer.concatenate()
    session.audio_buffer.clear()
    session.turn_context.reset()

    voice_turn = VoiceTurn(
        stt=stt,
        llm=backend,
        tts=tts,
        websocket=WebSocketConnection(session.websocket),
        config=SynthesisConfig(
            data_buffer_size=TTS_DATA_BUFFER_SIZE,
            time_buffer_seconds=TTS_TIME_BUFFER_SECONDS,
            sample_rate=TTS_SAMPLE_RATE,
            subtitle_streaming=SUBTITLE_STREAMING,
        ),
        turn_context=session.turn_context,
    )
    task = asyncio.create_task(voice_turn.execute(audio_data))
    session.start_response(task)
    return task


async def handle_interrupt(session: WebSocketSession) -> None:
    """Handle interrupt: cancels current response."""
    await session.websocket.send_json({"type": "interrupt_ack"})
    await session.cancel_response(send_interrupt_event=True)


async def handle_audio(
    session: WebSocketSession,
    message: AudioMessage,
    vad: "VoiceActivityDetector | None",
) -> bool:
    """Handle audio: buffers audio and optionally reports VAD status."""
    import numpy as np

    if not session.is_listening:
        return False

    audio_np = np.frombuffer(message.audio_data, dtype=np.float32)
    session.audio_buffer.append(audio_np)

    if vad and len(audio_np) > 0:
        has_speech = vad.is_speech(audio_np)
        await session.websocket.send_json({
            "type": "vad_status",
            "speech_detected": has_speech,
        })
    return True


async def handle_ping(session: WebSocketSession) -> None:
    """Handle ping: respond with pong."""
    await session.websocket.send_json({"type": "pong"})


async def handle_perf_report(
    session: WebSocketSession,
    message: PerfReportMessage,
    perf_logger,
    last_transcript: str,
    last_response: str,
    last_perf_data: dict,
    settings,
    backend: "BaseLLM",
) -> None:
    """Handle perf_report: logs performance metrics."""
    if perf_logger.is_enabled():
        frontend_metrics = message.metrics
        context = {
            "transcript": last_transcript,
            "response_length": len(last_response),
            "tts_model": settings.tts_model,
            "llm_model": backend.model_name if backend else "unknown",
            "tts_voice": settings.tts_voice,
        }
        perf_logger.log_round(
            frontend_data=frontend_metrics,
            backend_data=last_perf_data,
            context=context,
        )
