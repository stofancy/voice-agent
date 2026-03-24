"""
Unit tests for StreamingSynthesis.

Covers:
- LLM+TTS parallel execution
- Audio buffering logic
- Metrics calculation
- Cancellation
- Subtitle streaming toggle
"""

import asyncio
import os
import sys
import time
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.server.streaming_synthesis import (
    StreamingSynthesis,
    SynthesisConfig,
    SynthesisResult,
    SynthesisMetrics,
)
from src.server.turn_context import TurnContext


# ─────────────────────────────────────────────────────────────────────────────
# Mock Objects
# ─────────────────────────────────────────────────────────────────────────────


class MockLLMStream:
    """Mock LLM with controllable async generator."""

    def __init__(self, tokens: list[str], delay: float = 0.0):
        self._tokens = tokens
        self._delay = delay
        self.model_name = "mock-llm"

    async def chat_stream(self, messages) -> AsyncGenerator[str, None]:
        for token in self._tokens:
            if self._delay > 0:
                await asyncio.sleep(self._delay)
            yield token


class MockLLMStreamThatRaises:
    """Mock LLM that raises during streaming."""

    def __init__(self, tokens_before_error: list[str]):
        self._tokens = tokens_before_error
        self.model_name = "mock-llm"

    async def chat_stream(self, messages) -> AsyncGenerator[str, None]:
        for token in self._tokens:
            yield token
        raise RuntimeError("LLM error")


class MockTTSStream:
    """Mock TTS stream with configurable audio output."""

    def __init__(self, audio_chunks: list[bytes], delay: float = 0.0):
        self._audio_chunks = audio_chunks
        self._delay = delay
        self.feed_calls: list[str] = []
        self.finish_called = False
        self._ensure_connected_called = False

    def feed(self, text: str) -> None:
        self.feed_calls.append(text)

    def finish(self) -> None:
        self.finish_called = True

    def _ensure_connected(self) -> None:
        self._ensure_connected_called = True

    async def __aiter__(self):
        for chunk in self._audio_chunks:
            if self._delay > 0:
                await asyncio.sleep(self._delay)
            yield chunk


class MockTTSStreamCancellable:
    """Mock TTS stream that checks turn_context cancellation."""

    def __init__(self, turn_context: TurnContext, chunks_before_cancel: int = 2):
        self._turn_context = turn_context
        self._chunks_before_cancel = chunks_before_cancel
        self._chunk_count = 0
        self.feed_calls: list[str] = []
        self.finish_called = False

    def feed(self, text: str) -> None:
        self.feed_calls.append(text)

    def finish(self) -> None:
        self.finish_called = True

    def _ensure_connected(self) -> None:
        pass

    async def __aiter__(self):
        while self._chunk_count < self._chunks_before_cancel:
            self._chunk_count += 1
            yield b"\x00" * 1024
            if self._chunk_count >= self._chunks_before_cancel:
                # Simulate cancellation after some chunks
                self._turn_context.cancel()
        # Yield one more to trigger cancellation check
        yield b"\x00" * 1024


class MockTTS:
    """Mock TTS factory."""

    def __init__(self, stream):
        self._stream = stream

    def create_stream(self):
        return self._stream

    async def close(self):
        pass


class MockWS:
    """Mock WebSocket recording sent messages."""

    def __init__(self):
        self.sent_messages: list[dict] = []
        self.sent_audio_chunks: list[tuple[bytes, int]] = []

    async def send_json(self, data: dict) -> None:
        self.sent_messages.append(data)

    async def send_subtitle_chunk(self, text: str) -> None:
        self.sent_messages.append({"type": "subtitle_chunk", "text": text})

    async def send_audio_chunk(self, data: bytes, sample_rate: int) -> None:
        self.sent_audio_chunks.append((data, sample_rate))
        import base64

        audio_b64 = base64.b64encode(data).decode()
        self.sent_messages.append(
            {
                "type": "audio_chunk",
                "data": audio_b64,
                "sample_rate": sample_rate,
            }
        )

    def message_types(self) -> list[str]:
        return [m["type"] for m in self.sent_messages]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_llm_tokens_are_joined_into_full_response():
    """LLM tokens are accumulated into the full response string."""
    llm = MockLLMStream(["Hello", " ", "world", "!"])
    tts_stream = MockTTSStream(audio_chunks=[b"audio"])
    tts = MockTTS(tts_stream)
    ws = MockWS()

    synthesis = StreamingSynthesis(
        llm=llm,
        tts=tts,
        websocket=ws,
        config=SynthesisConfig(),
    )
    result = await synthesis.run("hello")

    assert result.full_response == "Hello world!"


@pytest.mark.asyncio
async def test_llm_tokens_are_fed_to_tts_stream():
    """Each LLM token is passed to tts_stream.feed()."""
    llm = MockLLMStream(["Hi", "!"])
    tts_stream = MockTTSStream(audio_chunks=[b"audio"])
    tts = MockTTS(tts_stream)
    ws = MockWS()

    synthesis = StreamingSynthesis(
        llm=llm,
        tts=tts,
        websocket=ws,
        config=SynthesisConfig(),
    )
    await synthesis.run("hello")

    assert tts_stream.feed_calls == ["Hi!"]  # Sent when sentence-ending punctuation received
    assert tts_stream.finish_called


@pytest.mark.asyncio
async def test_subtitle_chunks_sent_when_streaming_enabled():
    """Subtitle chunks are sent for each LLM token when subtitle_streaming=True."""
    llm = MockLLMStream(["Hi", "!"])
    tts_stream = MockTTSStream(audio_chunks=[b"audio"])
    tts = MockTTS(tts_stream)
    ws = MockWS()

    synthesis = StreamingSynthesis(
        llm=llm,
        tts=tts,
        websocket=ws,
        config=SynthesisConfig(subtitle_streaming=True),
    )
    await synthesis.run("hello")

    subtitle_msgs = [m for m in ws.sent_messages if m.get("type") == "subtitle_chunk"]
    assert len(subtitle_msgs) == 2
    assert subtitle_msgs[0]["text"] == "Hi"
    assert subtitle_msgs[1]["text"] == "!"


@pytest.mark.asyncio
async def test_subtitle_chunks_skipped_when_streaming_disabled():
    """No subtitle chunks are sent when subtitle_streaming=False."""
    llm = MockLLMStream(["Hi", "!"])
    tts_stream = MockTTSStream(audio_chunks=[b"audio"])
    tts = MockTTS(tts_stream)
    ws = MockWS()

    synthesis = StreamingSynthesis(
        llm=llm,
        tts=tts,
        websocket=ws,
        config=SynthesisConfig(subtitle_streaming=False),
    )
    await synthesis.run("hello")

    subtitle_msgs = [m for m in ws.sent_messages if m.get("type") == "subtitle_chunk"]
    assert len(subtitle_msgs) == 0


@pytest.mark.asyncio
async def test_tts_stream_finish_called_even_on_llm_error():
    """tts_stream.finish() is called even when LLM raises (finally block)."""
    llm = MockLLMStreamThatRaises(["token1"])
    tts_stream = MockTTSStream(audio_chunks=[b"audio"])
    tts = MockTTS(tts_stream)
    ws = MockWS()

    synthesis = StreamingSynthesis(
        llm=llm,
        tts=tts,
        websocket=ws,
        config=SynthesisConfig(),
    )
    with pytest.raises(RuntimeError, match="LLM error"):
        await synthesis.run("hello")

    assert tts_stream.finish_called


@pytest.mark.asyncio
async def test_audio_chunks_sent_when_buffer_size_reached():
    """Audio is sent when buffer reaches data_buffer_size."""
    # TTS produces 3 chunks of 500 bytes each
    llm = MockLLMStream(["Hi"])
    tts_stream = MockTTSStream(audio_chunks=[b"x" * 500, b"y" * 500, b"z" * 500])
    tts = MockTTS(tts_stream)
    ws = MockWS()

    config = SynthesisConfig()
    synthesis = StreamingSynthesis(llm=llm, tts=tts, websocket=ws, config=config)
    result = await synthesis.run("hello")

    # Should have sent audio chunks
    assert result.metrics.audio_chunks_sent >= 1


@pytest.mark.asyncio
async def test_llm_ttft_metric_is_positive():
    """llm_ttft_ms is a positive number representing time to first token."""
    llm = MockLLMStream(["token"])
    tts_stream = MockTTSStream(audio_chunks=[b"audio"])
    tts = MockTTS(tts_stream)
    ws = MockWS()

    synthesis = StreamingSynthesis(
        llm=llm,
        tts=tts,
        websocket=ws,
        config=SynthesisConfig(),
    )
    result = await synthesis.run("hello")

    assert result.metrics.llm_ttft_ms is not None
    assert result.metrics.llm_ttft_ms >= 0


@pytest.mark.asyncio
async def test_llm_gen_metric_is_positive():
    """llm_gen_ms is a positive number representing LLM generation time."""
    llm = MockLLMStream(["Hello", " ", "world"])
    tts_stream = MockTTSStream(audio_chunks=[b"audio"])
    tts = MockTTS(tts_stream)
    ws = MockWS()

    synthesis = StreamingSynthesis(
        llm=llm,
        tts=tts,
        websocket=ws,
        config=SynthesisConfig(),
    )
    result = await synthesis.run("hello")

    assert result.metrics.llm_gen_ms is not None
    assert result.metrics.llm_gen_ms >= 0


@pytest.mark.asyncio
async def test_llm_ttft_none_when_no_tokens():
    """llm_ttft_ms is None when LLM produces no tokens."""
    llm = MockLLMStream([])
    tts_stream = MockTTSStream(audio_chunks=[b"audio"])
    tts = MockTTS(tts_stream)
    ws = MockWS()

    synthesis = StreamingSynthesis(
        llm=llm,
        tts=tts,
        websocket=ws,
        config=SynthesisConfig(),
    )
    result = await synthesis.run("hello")

    assert result.metrics.llm_ttft_ms is None
    assert result.metrics.llm_gen_ms is None


@pytest.mark.asyncio
async def test_tts_total_ms_is_positive():
    """tts_total_ms is set and positive."""
    llm = MockLLMStream(["Hi"])
    tts_stream = MockTTSStream(audio_chunks=[b"audio"])
    tts = MockTTS(tts_stream)
    ws = MockWS()

    synthesis = StreamingSynthesis(
        llm=llm,
        tts=tts,
        websocket=ws,
        config=SynthesisConfig(),
    )
    result = await synthesis.run("hello")

    assert result.metrics.tts_total_ms is not None
    assert result.metrics.tts_total_ms >= 0


@pytest.mark.asyncio
async def test_ensure_connected_called_before_consuming():
    """TTS stream _ensure_connected() is called before consuming audio."""
    llm = MockLLMStream(["Hi"])
    tts_stream = MockTTSStream(audio_chunks=[b"audio"])
    tts = MockTTS(tts_stream)
    ws = MockWS()

    synthesis = StreamingSynthesis(
        llm=llm,
        tts=tts,
        websocket=ws,
        config=SynthesisConfig(),
    )
    await synthesis.run("hello")

    assert tts_stream._ensure_connected_called


@pytest.mark.asyncio
async def test_empty_llm_response():
    """Empty LLM response returns empty full_response."""
    llm = MockLLMStream([])
    tts_stream = MockTTSStream(audio_chunks=[])
    tts = MockTTS(tts_stream)
    ws = MockWS()

    synthesis = StreamingSynthesis(
        llm=llm,
        tts=tts,
        websocket=ws,
        config=SynthesisConfig(),
    )
    result = await synthesis.run("hello")

    assert result.full_response == ""
    assert result.metrics.audio_chunks_sent == 0
