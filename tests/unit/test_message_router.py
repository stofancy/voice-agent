"""
Unit tests for message_router handlers.

Covers:
- handle_start_listening
- handle_stop_listening (not listening, empty buffer, success)
- handle_audio (not listening, with VAD, without VAD)
- handle_interrupt
- handle_ping
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.server.connection import ConnectionState, ConnectionStateMachine
from src.server.websocket_session import WebSocketSession
from src.server.audio import AudioBuffer
from src.server.turn_context import TurnContext
from src.server.messages import AudioMessage, MessageType


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────


def make_session(
    state: ConnectionState = ConnectionState.IDLE,
    audio_chunks: list[np.ndarray] | None = None,
) -> tuple[WebSocketSession, MagicMock]:
    """Create a WebSocketSession with mock websocket."""
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.close = AsyncMock()

    # Create a WebSocket object matching the protocol
    mock_real_ws = MagicMock()
    mock_real_ws.send_json = AsyncMock()

    session = WebSocketSession(mock_real_ws)
    session.connection_state = ConnectionStateMachine()
    session.connection_state.transition_to(state)

    if audio_chunks:
        for chunk in audio_chunks:
            session.audio_buffer.append(chunk)

    return session, mock_real_ws


def make_audio_message(audio_bytes: bytes) -> AudioMessage:
    """Create an AudioMessage from raw bytes."""
    return AudioMessage(
        type=MessageType.AUDIO,
        data={"data": audio_bytes.hex()},  # Not used
        audio_data=audio_bytes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# handle_start_listening
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_start_listening_sets_listening_state():
    """handle_start_listening transitions state to LISTENING."""
    from src.server.message_router import handle_start_listening

    session, ws = make_session(state=ConnectionState.IDLE)

    await handle_start_listening(session)

    assert session.connection_state.is_listening()


@pytest.mark.asyncio
async def test_handle_start_listening_sends_listening_started():
    """handle_start_listening sends listening_started message."""
    from src.server.message_router import handle_start_listening

    session, ws = make_session(state=ConnectionState.IDLE)

    await handle_start_listening(session)

    ws.send_json.assert_called_with({"type": "listening_started"})


@pytest.mark.asyncio
async def test_handle_start_listening_clears_audio_buffer():
    """handle_start_listening clears the audio buffer."""
    from src.server.message_router import handle_start_listening

    session, ws = make_session(
        state=ConnectionState.IDLE,
        audio_chunks=[np.zeros(100, dtype=np.float32)],
    )
    assert not session.audio_buffer.is_empty()

    await handle_start_listening(session)

    assert session.audio_buffer.is_empty()


# ─────────────────────────────────────────────────────────────────────────────
# handle_stop_listening
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_stop_listening_not_listening_returns_none():
    """handle_stop_listening returns None when not in LISTENING state."""
    from src.server.message_router import handle_stop_listening

    session, ws = make_session(state=ConnectionState.IDLE)

    result = await handle_stop_listening(
        session=session,
        stt=MagicMock(),
        backend=MagicMock(),
        tts=MagicMock(),
        TTS_SAMPLE_RATE=24000,
        SUBTITLE_STREAMING=True,
    )

    assert result is None


@pytest.mark.asyncio
async def test_handle_stop_listening_not_listening_sends_stopped():
    """handle_stop_listening sends listening_stopped when not listening."""
    from src.server.message_router import handle_stop_listening

    session, ws = make_session(state=ConnectionState.IDLE)

    await handle_stop_listening(
        session=session,
        stt=MagicMock(),
        backend=MagicMock(),
        tts=MagicMock(),
        TTS_SAMPLE_RATE=24000,
        SUBTITLE_STREAMING=True,
    )

    # send_listening_stopped sends listening_stopped JSON
    calls = [str(c) for c in ws.send_json.call_args_list]
    assert any("listening_stopped" in c for c in calls)


@pytest.mark.asyncio
async def test_handle_stop_listening_empty_buffer_returns_none():
    """handle_stop_listening returns None when audio buffer is empty."""
    from src.server.message_router import handle_stop_listening

    session, ws = make_session(state=ConnectionState.LISTENING)
    # Buffer is empty by default

    result = await handle_stop_listening(
        session=session,
        stt=MagicMock(),
        backend=MagicMock(),
        tts=MagicMock(),
        TTS_SAMPLE_RATE=24000,
        SUBTITLE_STREAMING=True,
    )

    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# handle_audio
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_audio_not_listening_returns_false():
    """handle_audio returns False when not in LISTENING state."""
    from src.server.message_router import handle_audio

    session, ws = make_session(state=ConnectionState.IDLE)
    msg = make_audio_message(b"\x00" * 1024)

    result = await handle_audio(session=session, message=msg, vad=None)

    assert result is False


@pytest.mark.asyncio
async def test_handle_audio_listening_returns_true():
    """handle_audio returns True when in LISTENING state."""
    from src.server.message_router import handle_audio

    session, ws = make_session(state=ConnectionState.LISTENING)
    msg = make_audio_message(b"\x00" * 1024)

    result = await handle_audio(session=session, message=msg, vad=None)

    assert result is True


@pytest.mark.asyncio
async def test_handle_audio_appends_to_buffer():
    """handle_audio appends audio data to the session buffer."""
    from src.server.message_router import handle_audio

    session, ws = make_session(state=ConnectionState.LISTENING)
    audio_data = np.zeros(256, dtype=np.float32).tobytes()
    msg = make_audio_message(audio_data)

    await handle_audio(session=session, message=msg, vad=None)

    assert not session.audio_buffer.is_empty()


@pytest.mark.asyncio
async def test_handle_audio_without_vad_no_vad_status():
    """handle_audio without VAD does not send vad_status."""
    from src.server.message_router import handle_audio

    session, ws = make_session(state=ConnectionState.LISTENING)
    audio_data = np.zeros(256, dtype=np.float32).tobytes()
    msg = make_audio_message(audio_data)

    await handle_audio(session=session, message=msg, vad=None)

    types_sent = [str(c) for c in ws.send_json.call_args_list]
    assert not any("vad_status" in c for c in types_sent)


@pytest.mark.asyncio
async def test_handle_audio_with_vad_sends_vad_status():
    """handle_audio with VAD sends vad_status message."""
    from src.server.message_router import handle_audio

    session, ws = make_session(state=ConnectionState.LISTENING)
    audio_data = np.zeros(256, dtype=np.float32).tobytes()
    msg = make_audio_message(audio_data)

    mock_vad = MagicMock()
    mock_vad.is_speech = MagicMock(return_value=True)

    await handle_audio(session=session, message=msg, vad=mock_vad)

    mock_vad.is_speech.assert_called_once()
    ws.send_json.assert_called()
    call_data = ws.send_json.call_args[0][0]
    assert call_data["type"] == "vad_status"
    assert call_data["speech_detected"] is True


@pytest.mark.asyncio
async def test_handle_audio_with_vad_empty_audio_skips_vad():
    """handle_audio with empty audio skips VAD processing."""
    from src.server.message_router import handle_audio

    session, ws = make_session(state=ConnectionState.LISTENING)
    msg = make_audio_message(b"")

    mock_vad = MagicMock()
    mock_vad.is_speech = MagicMock(return_value=True)

    result = await handle_audio(session=session, message=msg, vad=mock_vad)

    assert result is True
    mock_vad.is_speech.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# handle_interrupt
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_interrupt_sends_interrupt_ack():
    """handle_interrupt sends interrupt_ack message."""
    from src.server.message_router import handle_interrupt

    session, ws = make_session(state=ConnectionState.SPEAKING)

    await handle_interrupt(session)

    # handle_interrupt sends interrupt_ack first, then interrupt_complete via cancel_response
    all_calls = [c[0][0] for c in ws.send_json.call_args_list]
    types_sent = [c["type"] for c in all_calls]
    assert "interrupt_ack" in types_sent
    assert "interrupt_complete" in types_sent


# ─────────────────────────────────────────────────────────────────────────────
# handle_ping
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_ping_sends_pong():
    """handle_ping sends pong message."""
    from src.server.message_router import handle_ping

    session, ws = make_session(state=ConnectionState.IDLE)

    await handle_ping(session)

    call_data = ws.send_json.call_args[0][0]
    assert call_data["type"] == "pong"
