"""
Message handler functions for WebSocket message handling.

These functions are extracted from the websocket_endpoint if/elif chain
to improve maintainability. They can be called directly from the existing
message loop or via a MessageRouter.
"""

from typing import TYPE_CHECKING, Awaitable, Callable, Optional

from .connection import ConnectionState, ConnectionStateMachine, WebSocketConnection

if TYPE_CHECKING:
    from fastapi import WebSocket
    from .audio import AudioBuffer
    from .turn_context import TurnContext
    from .llm import BaseLLM
    from .tts import BaseTTS
    from .stt import BaseSTT
    from .vad import VoiceActivityDetector
    from .streaming_synthesis import SynthesisConfig
    from .messages import WSMessage, StartListeningMessage, StopListeningMessage, AudioMessage, PerfReportMessage


async def handle_start_listening(
    websocket: "WebSocket",
    connection_state: ConnectionStateMachine,
    audio_buffer: "AudioBuffer",
    cancel_callback: Callable[[bool], Awaitable],
) -> None:
    """
    Handle start_listening message.

    Args:
        websocket: FastAPI WebSocket
        connection_state: ConnectionStateMachine instance
        audio_buffer: AudioBuffer instance
        cancel_callback: Function to cancel current response
    """
    await cancel_callback(send_interrupt_event=False)
    audio_buffer.clear()
    connection_state.transition_to(ConnectionState.LISTENING)
    await websocket.send_json({"type": "listening_started"})


async def handle_stop_listening(
    websocket: "WebSocket",
    connection_state: ConnectionStateMachine,
    audio_buffer: "AudioBuffer",
    turn_context: "TurnContext",
    send_listening_stopped_once: Callable[[], Awaitable],
    stt: "BaseSTT",
    backend: "BaseLLM",
    tts: "BaseTTS",
    TTS_DATA_BUFFER_SIZE: int,
    TTS_TIME_BUFFER_SECONDS: float,
    TTS_SAMPLE_RATE: int,
    SUBTITLE_STREAMING: bool,
) -> Optional["asyncio.Task"]:
    """
    Handle stop_listening message.

    Args:
        websocket: FastAPI WebSocket
        connection_state: ConnectionStateMachine instance
        audio_buffer: AudioBuffer instance
        turn_context: TurnContext instance
        send_listening_stopped_once: Function to send listening_stopped
        stt: BaseSTT instance
        backend: BaseLLM instance
        tts: BaseTTS instance
        TTS_DATA_BUFFER_SIZE: TTS data buffer size
        TTS_TIME_BUFFER_SECONDS: TTS time buffer in seconds
        TTS_SAMPLE_RATE: TTS sample rate
        SUBTITLE_STREAMING: Whether to stream subtitles

    Returns:
        The created task if turn started, None if skipped
    """
    import asyncio
    from .voice_turn import VoiceTurn
    from .streaming_synthesis import SynthesisConfig

    if not connection_state.is_listening():
        await send_listening_stopped_once()
        return None

    if not audio_buffer:
        await send_listening_stopped_once()
        return None

    audio_data = audio_buffer.concatenate()
    audio_buffer.clear()
    turn_context.reset()

    voice_turn = VoiceTurn(
        stt=stt,
        llm=backend,
        tts=tts,
        websocket=WebSocketConnection(websocket),
        config=SynthesisConfig(
            data_buffer_size=TTS_DATA_BUFFER_SIZE,
            time_buffer_seconds=TTS_TIME_BUFFER_SECONDS,
            sample_rate=TTS_SAMPLE_RATE,
            subtitle_streaming=SUBTITLE_STREAMING,
        ),
        turn_context=turn_context,
    )
    return asyncio.create_task(voice_turn.execute(audio_data))


async def handle_interrupt(
    websocket: "WebSocket",
    cancel_callback: Callable[[bool], Awaitable],
) -> None:
    """
    Handle interrupt message.

    Args:
        websocket: FastAPI WebSocket
        cancel_callback: Function to cancel current response
    """
    await websocket.send_json({"type": "interrupt_ack"})
    await cancel_callback(send_interrupt_event=True)


async def handle_audio(
    message: "AudioMessage",
    websocket: "WebSocket",
    connection_state: ConnectionStateMachine,
    audio_buffer: "AudioBuffer",
    vad: "VoiceActivityDetector | None",
) -> bool:
    """
    Handle audio message (only when in LISTENING state).

    Args:
        message: AudioMessage with audio data
        websocket: FastAPI WebSocket
        connection_state: ConnectionStateMachine instance
        audio_buffer: AudioBuffer instance
        vad: VoiceActivityDetector instance or None

    Returns:
        True if message was handled, False if not listening
    """
    import numpy as np

    if not connection_state.is_listening():
        return False

    audio_np = np.frombuffer(message.audio_data, dtype=np.float32)
    audio_buffer.append(audio_np)

    if vad and len(audio_np) > 0:
        has_speech = vad.is_speech(audio_np)
        await websocket.send_json(
            {
                "type": "vad_status",
                "speech_detected": has_speech,
            }
        )
    return True


async def handle_ping(
    websocket: "WebSocket",
) -> None:
    """
    Handle ping message.

    Args:
        websocket: FastAPI WebSocket
    """
    await websocket.send_json({"type": "pong"})


async def handle_perf_report(
    message: "PerfReportMessage",
    perf_logger,  # perf_logger module
    last_transcript: str,
    last_response: str,
    last_perf_data: dict,
    settings,
    backend,
) -> None:
    """
    Handle perf_report message.

    Args:
        message: PerfReportMessage with metrics
        perf_logger: perf_logger module
        last_transcript: Last transcription text
        last_response: Last LLM response text
        last_perf_data: Last performance data dict
        settings: Settings instance
        backend: BaseLLM instance
    """
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
