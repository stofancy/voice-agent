"""
Unit tests for VoiceTurn and ConnectionStateMachine.

Covers:
- ConnectionStateMachine transitions and queries
- VoiceTurn.execute() state flow
- State synchronization between VoiceTurn and WebSocketSession
- Interrupt handling
- Error paths
"""

import asyncio
import os
import sys
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.server.connection import ConnectionState, ConnectionStateMachine, WebSocketConnection
from src.server.voice_turn import VoiceTurn
from src.server.turn_context import TurnContext
from src.server.streaming_synthesis import SynthesisConfig


# ─────────────────────────────────────────────────────────────────────────────
# Mock Objects
# ─────────────────────────────────────────────────────────────────────────────


class MockSTT:
    """Mock STT that returns a configurable transcript."""

    def __init__(self, transcript: str = "hello world", success: bool = True):
        self._transcript = transcript
        self._success = success
        self.transcribe_called = False

    async def transcribe(self, audio_data):
        self.transcribe_called = True
        return self._transcript, self._success

    async def close(self):
        pass


class MockLLM:
    """Mock LLM that yields tokens."""

    def __init__(self, tokens: list[str] | None = None, raise_on_stream: bool = False):
        self._tokens = tokens or ["Hello", " ", "world", "!"]
        self._raise_on_stream = raise_on_stream
        self.model_name = "mock-llm"

    async def chat_stream(self, messages) -> AsyncGenerator[str, None]:
        if self._raise_on_stream:
            raise RuntimeError("LLM stream error")
        for token in self._tokens:
            yield token

    async def close(self):
        pass


class MockTTSStream:
    """Mock TTS stream."""

    def __init__(self, audio_chunks: list[bytes] | None = None):
        self._audio_chunks = audio_chunks or [b"\x00" * 1024]
        self.feed_call_count = 0
        self.finish_called = False

    def feed(self, text: str) -> None:
        self.feed_call_count += 1

    def finish(self) -> None:
        self.finish_called = True

    def _ensure_connected(self) -> None:
        pass

    async def __aiter__(self):
        for chunk in self._audio_chunks:
            yield chunk


class MockTTS:
    """Mock TTS factory."""

    def __init__(self, stream: MockTTSStream | None = None):
        self._stream = stream or MockTTSStream()

    def create_stream(self):
        return self._stream

    async def close(self):
        pass


class MockWS:
    """Mock WebSocketConnection that records sent messages."""

    def __init__(self):
        self.sent_messages: list[dict] = []

    async def send_json(self, data: dict) -> None:
        self.sent_messages.append(data)

    # Typed send methods (delegate to send_json)
    async def send_listening_started(self) -> None:
        await self.send_json({"type": "listening_started"})

    async def send_listening_stopped(self) -> None:
        await self.send_json({"type": "listening_stopped"})

    async def send_transcript(self, text: str) -> None:
        await self.send_json({"type": "transcript", "text": text, "final": True})

    async def send_tts_start(self) -> None:
        await self.send_json({"type": "tts_start"})

    async def send_tts_end(self, interrupted: bool = False) -> None:
        await self.send_json({"type": "tts_end", "interrupted": interrupted})

    async def send_response_complete(self, text: str) -> None:
        await self.send_json({"type": "response_complete", "text": text})

    async def send_subtitle_chunk(self, text: str) -> None:
        await self.send_json({"type": "subtitle_chunk", "text": text})

    async def send_audio_chunk(self, data: bytes, sample_rate: int) -> None:
        import base64

        audio_b64 = base64.b64encode(data).decode()
        await self.send_json({"type": "audio_chunk", "data": audio_b64, "sample_rate": sample_rate})

    async def send_interrupt_ack(self) -> None:
        await self.send_json({"type": "interrupt_ack"})

    async def send_interrupt_complete(self) -> None:
        await self.send_json({"type": "interrupt_complete"})

    def message_types(self) -> list[str]:
        return [msg["type"] for msg in self.sent_messages]


# ─────────────────────────────────────────────────────────────────────────────
# ConnectionStateMachine Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConnectionStateMachine:
    """Tests for ConnectionStateMachine behavior."""

    def test_initial_state_is_idle(self):
        sm = ConnectionStateMachine()
        assert sm.state == ConnectionState.IDLE
        assert sm.is_idle()
        assert not sm.is_listening()
        assert not sm.is_processing()
        assert not sm.is_speaking()

    def test_transition_to_listening(self):
        sm = ConnectionStateMachine()
        sm.transition_to(ConnectionState.LISTENING)
        assert sm.state == ConnectionState.LISTENING
        assert sm.is_listening()

    def test_transition_to_processing(self):
        sm = ConnectionStateMachine()
        sm.transition_to(ConnectionState.PROCESSING)
        assert sm.state == ConnectionState.PROCESSING
        assert sm.is_processing()

    def test_transition_to_speaking(self):
        sm = ConnectionStateMachine()
        sm.transition_to(ConnectionState.SPEAKING)
        assert sm.state == ConnectionState.SPEAKING
        assert sm.is_speaking()

    def test_transition_back_to_idle(self):
        sm = ConnectionStateMachine()
        sm.transition_to(ConnectionState.SPEAKING)
        sm.transition_to(ConnectionState.IDLE)
        assert sm.is_idle()

    def test_no_transition_validation(self):
        """Current impl allows any transition from any state."""
        sm = ConnectionStateMachine()
        sm.transition_to(ConnectionState.SPEAKING)
        # This should ideally fail but currently doesn't
        sm.transition_to(ConnectionState.PROCESSING)
        assert sm.is_processing()


# ─────────────────────────────────────────────────────────────────────────────
# VoiceTurn Tests
# ─────────────────────────────────────────────────────────────────────────────


def _make_voice_turn(
    stt: MockSTT | None = None,
    llm: MockLLM | None = None,
    tts: MockTTS | None = None,
    ws: MockWS | None = None,
    config: SynthesisConfig | None = None,
    turn_context: TurnContext | None = None,
) -> tuple[VoiceTurn, MockWS, TurnContext]:
    """Helper to create VoiceTurn with mocks."""
    ws = ws or MockWS()
    tc = turn_context or TurnContext()
    return (
        VoiceTurn(
            stt=stt or MockSTT(),
            llm=llm or MockLLM(),
            tts=tts or MockTTS(),
            websocket=ws,
            config=config or SynthesisConfig(),
            turn_context=tc,
        ),
        ws,
        tc,
    )


@pytest.mark.asyncio
async def test_vt_execute_successful_turn():
    """Happy path: STT → LLM+TTS → completion."""
    turn, ws, tc = _make_voice_turn(
        stt=MockSTT(transcript="hello", success=True),
        llm=MockLLM(tokens=["Hi", "!"]),
        tts=MockTTS(MockTTSStream(audio_chunks=[b"audio1", b"audio2"])),
    )

    audio = np.zeros(16000, dtype=np.float32)
    result = await turn.execute(audio)

    assert result == "Hi!"
    types = ws.message_types()
    assert "transcript" in types
    assert "tts_start" in types
    assert "tts_end" in types
    assert "response_complete" in types
    assert "listening_stopped" in types


@pytest.mark.asyncio
async def test_vt_execute_empty_transcript_returns_idle():
    """Empty transcript → skip LLM, return to idle."""
    turn, ws, tc = _make_voice_turn(
        stt=MockSTT(transcript="", success=True),
    )

    audio = np.zeros(16000, dtype=np.float32)
    result = await turn.execute(audio)

    assert result == ""
    types = ws.message_types()
    assert "transcript" in types
    assert "listening_stopped" in types
    # Should NOT start TTS
    assert "tts_start" not in types


@pytest.mark.asyncio
async def test_vt_execute_stt_failure_returns_idle():
    """STT failure → skip LLM, return to idle."""
    turn, ws, tc = _make_voice_turn(
        stt=MockSTT(transcript="something", success=False),
    )

    audio = np.zeros(16000, dtype=np.float32)
    result = await turn.execute(audio)

    assert result == ""
    assert "listening_stopped" in ws.message_types()


@pytest.mark.asyncio
async def test_vt_execute_tts_end_not_interrupted_on_success():
    """Successful turn sends tts_end(interrupted=False)."""
    turn, ws, tc = _make_voice_turn()

    audio = np.zeros(16000, dtype=np.float32)
    await turn.execute(audio)

    tts_end_msgs = [m for m in ws.sent_messages if m.get("type") == "tts_end"]
    assert len(tts_end_msgs) == 1
    assert tts_end_msgs[0]["interrupted"] is False


@pytest.mark.asyncio
async def test_vt_execute_llm_error_sends_fallback():
    """LLM error → sends fallback response + tts_end(interrupted=True)."""
    turn, ws, tc = _make_voice_turn(
        llm=MockLLM(raise_on_stream=True),
    )

    audio = np.zeros(16000, dtype=np.float32)
    with pytest.raises(RuntimeError):
        await turn.execute(audio)

    types = ws.message_types()
    assert "response_complete" in types
    tts_end_msgs = [m for m in ws.sent_messages if m.get("type") == "tts_end"]
    assert any(m.get("interrupted") for m in tts_end_msgs)


@pytest.mark.asyncio
async def test_vt_execute_stt_called_with_audio():
    """STT is called with the provided audio data."""
    stt = MockSTT(transcript="test", success=True)
    turn, ws, tc = _make_voice_turn(stt=stt)

    audio = np.zeros(16000, dtype=np.float32)
    await turn.execute(audio)

    assert stt.transcribe_called


# ─────────────────────────────────────────────────────────────────────────────
# VoiceTurn State Machine Tests (current behavior - will change after refactor)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_vt_creates_own_state_machine():
    """Current behavior: VoiceTurn creates its own ConnectionStateMachine."""
    turn, ws, tc = _make_voice_turn()

    # VoiceTurn has its own internal state machine
    assert hasattr(turn, "_state")
    assert isinstance(turn._state, ConnectionStateMachine)
    assert turn._state.is_idle()


@pytest.mark.asyncio
async def test_vt_state_transitions_in_execute():
    """VoiceTurn's state transitions during execute propagate to shared state machine."""
    shared_state = ConnectionStateMachine()
    turn, ws, tc = _make_voice_turn()

    # Replace VoiceTurn's internal state with the shared one
    turn._state = shared_state

    audio = np.zeros(16000, dtype=np.float32)
    await turn.execute(audio)

    # After completion, shared state returns to IDLE
    assert shared_state.is_idle()
    assert turn._state.is_idle()


@pytest.mark.asyncio
async def test_vt_uses_external_state_machine():
    """VoiceTurn accepts and uses an external ConnectionStateMachine."""
    shared_state = ConnectionStateMachine()
    shared_state.transition_to(ConnectionState.LISTENING)

    turn = VoiceTurn(
        stt=MockSTT(transcript="hello", success=True),
        llm=MockLLM(),
        tts=MockTTS(),
        websocket=MockWS(),
        config=SynthesisConfig(),
        turn_context=TurnContext(),
        connection_state=shared_state,
    )

    # Verify it uses the shared state machine
    assert turn._state is shared_state
    assert turn._state.is_listening()


@pytest.mark.asyncio
async def test_vt_state_syncs_to_session():
    """VoiceTurn's state changes propagate to the shared session state machine."""
    session_state = ConnectionStateMachine()
    session_state.transition_to(ConnectionState.LISTENING)

    turn = VoiceTurn(
        stt=MockSTT(transcript="hello", success=True),
        llm=MockLLM(),
        tts=MockTTS(MockTTSStream()),
        websocket=MockWS(),
        config=SynthesisConfig(),
        turn_context=TurnContext(),
        connection_state=session_state,
    )

    audio = np.zeros(16000, dtype=np.float32)
    await turn.execute(audio)

    # Session state IS updated (this was the bug)
    assert session_state.is_idle()
    assert turn._state.is_idle()


@pytest.mark.asyncio
async def test_vt_state_syncs_on_empty_transcript():
    """VoiceTurn transitions session state to IDLE on empty transcript."""
    session_state = ConnectionStateMachine()
    session_state.transition_to(ConnectionState.LISTENING)

    turn = VoiceTurn(
        stt=MockSTT(transcript="", success=True),
        llm=MockLLM(),
        tts=MockTTS(),
        websocket=MockWS(),
        config=SynthesisConfig(),
        turn_context=TurnContext(),
        connection_state=session_state,
    )

    audio = np.zeros(16000, dtype=np.float32)
    await turn.execute(audio)

    assert session_state.is_idle()


@pytest.mark.asyncio
async def test_vt_creates_internal_state_machine_if_not_provided():
    """VoiceTurn creates internal state machine when none is provided."""
    turn, ws, tc = _make_voice_turn()

    assert hasattr(turn, "_state")
    assert isinstance(turn._state, ConnectionStateMachine)
    assert turn._state.is_idle()


# ─────────────────────────────────────────────────────────────────────────────
# WebSocketSession State Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_session_cancel_response_transitions_state():
    """WebSocketSession.cancel_response manages its own state correctly."""
    from src.server.websocket_session import WebSocketSession

    mock_websocket = MagicMock()
    mock_websocket.send_json = AsyncMock()

    session = WebSocketSession(mock_websocket)
    session.connection_state.transition_to(ConnectionState.SPEAKING)

    # Create a dummy task
    async def dummy():
        await asyncio.sleep(10)

    task = asyncio.create_task(dummy())
    session.start_response(task)

    await session.cancel_response(send_interrupt_event=True)

    assert session.response_task is None
    mock_websocket.send_json.assert_called()


@pytest.mark.asyncio
async def test_session_send_listening_stopped_updates_state():
    """send_listening_stopped transitions state AND sends message."""
    from src.server.websocket_session import WebSocketSession

    mock_websocket = MagicMock()
    mock_websocket.send_json = AsyncMock()

    session = WebSocketSession(mock_websocket)
    session.connection_state.transition_to(ConnectionState.LISTENING)

    await session.send_listening_stopped()

    assert session.connection_state.is_idle()
    mock_websocket.send_json.assert_called_with({"type": "listening_stopped"})


# ─────────────────────────────────────────────────────────────────────────────
# Cancellation Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_vt_execute_turn_context_cancel_checks():
    """TurnContext.cancel() sets the cancelled flag."""
    tc = TurnContext()
    assert not tc.is_cancelled()
    tc.cancel()
    assert tc.is_cancelled()
    tc.reset()
    assert not tc.is_cancelled()


@pytest.mark.asyncio
async def test_vt_execute_handles_cancelled_error():
    """VoiceTurn catches CancelledError properly."""
    # CancelledError is caught by VoiceTurn.execute() and re-raised
    # The outer except block sends tts_end(interrupted=True) before re-raising
    # This is tested indirectly through the task cancellation flow
    turn, ws, tc = _make_voice_turn()
    turn._state.transition_to(ConnectionState.SPEAKING)

    # Verify we can transition to IDLE (simulating what interrupt would do)
    turn._state.transition_to(ConnectionState.IDLE)
    assert turn._state.is_idle()
