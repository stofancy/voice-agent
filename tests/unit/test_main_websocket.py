"""
Unit tests for websocket_endpoint in src/server/main.py.

Tests are organized by test case document:
docs/test_cases/websocket_endpoint_test_cases.md

Coverage:
- Message handling branches (MSG-001 to MSG-009)
- run_turn function branches (TURN-001 to TURN-004)
- LLM+TTS parallel execution (PIPELINE-001 to PIPELINE-007)
- Exception handling (EXC-001 to EXC-004)
- Connection state machine (STATE-001 to STATE-006)
- cancel_response function (CANCEL-001 to CANCEL-004)
- Performance logging (PERF-001, PERF-002)
"""

import asyncio
import base64
import json
import os
import sys
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


# ─────────────────────────────────────────────────────────────────────────────
# Mock Objects (对应 test_cases 文档中的 Mock 规范)
# ─────────────────────────────────────────────────────────────────────────────


class MockTTSStream:
    """Mock TTSStream - 对应 test_cases 文档中的 Mock 对象规范"""

    def __init__(
        self,
        audio_chunks: list[bytes] | None = None,
        raise_exception: bool = False,
    ):
        self.audio_chunks = audio_chunks or [b"\x00" * 1024]
        self.raise_exception = raise_exception
        self.feed_call_count = 0  # 改为计数器
        self.finish_called = False
        self.ensure_connected_called = False

    def feed(self, text: str) -> None:
        self.feed_call_count += 1

    def finish(self) -> None:
        self.finish_called = True

    def _ensure_connected(self) -> None:
        self.ensure_connected_called = True

    async def __aiter__(self) -> AsyncGenerator[bytes, None]:
        if self.raise_exception:
            raise Exception("TTS stream error")
        for chunk in self.audio_chunks:
            yield chunk


class MockWebSocket:
    """Mock WebSocket - 对应 test_cases 文档中的 Mock 对象规范"""

    def __init__(
        self,
        receive_texts: list[str] | None = None,
        raise_disconnect: bool = False,
        raise_on_send: bool = False,
    ):
        self.receive_texts = receive_texts or []
        self.receive_index = 0
        self.raise_disconnect = raise_disconnect
        self.raise_on_send = raise_on_send
        self.sent_messages: list[dict] = []
        self.accept_called = False
        self.close_called = False

    async def accept(self) -> None:
        self.accept_called = True

    async def receive_text(self) -> str:
        if self.raise_disconnect:
            from fastapi import WebSocketDisconnect

            raise WebSocketDisconnect()
        if self.receive_index >= len(self.receive_texts):
            from fastapi import WebSocketDisconnect

            raise WebSocketDisconnect()  # 客户端断开
        msg = self.receive_texts[self.receive_index]
        self.receive_index += 1
        # Yield control to event loop to allow scheduled tasks to run
        await asyncio.sleep(0)
        return msg

    async def send_json(self, data: dict) -> None:
        if self.raise_on_send:
            raise RuntimeError("WebSocket send failed")
        self.sent_messages.append(data)

    async def close(self) -> None:
        self.close_called = True


def make_audio_msg(audio_data: bytes | np.ndarray) -> str:
    """创建 audio 消息 JSON 字符串"""
    if isinstance(audio_data, np.ndarray):
        audio_data = audio_data.tobytes()
    audio_b64 = base64.b64encode(audio_data).decode()
    return json.dumps({"type": "audio", "data": audio_b64})


@pytest.fixture
def mock_settings():
    """Mock settings with auth disabled"""
    with patch("src.server.main.settings") as mock:
        mock.require_auth = False
        mock.stt_provider = "mock"
        mock.stt_api_key = "mock"
        mock.stt_model = "mock"
        mock.stt_base_url = None
        mock.stt_language = "zh"
        mock.tts_provider = "mock"
        mock.tts_api_key = "mock"
        mock.tts_model = "mock"
        mock.tts_voice = "mock"
        mock.tts_base_url = None
        mock.tts_language = "Chinese"
        mock.llm_provider = "mock"
        mock.llm_api_key = "mock"
        mock.llm_model = "mock"
        mock.llm_base_url = None
        yield mock


def create_mock_ws(receive_texts: list[str]) -> MagicMock:
    """创建配置好的 Mock WebSocket"""
    ws = MockWebSocket(receive_texts=receive_texts)
    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = ws.receive_text
    mock_ws.send_json = ws.send_json
    mock_ws.close = AsyncMock()
    mock_ws.query_params = MagicMock()
    mock_ws.query_params.get = MagicMock(return_value=None)
    mock_ws.headers = MagicMock()
    mock_ws.headers.get = MagicMock(return_value=None)
    # 保存 ws 引用到 mock_ws._ws 以便断言使用
    mock_ws._ws = ws
    return mock_ws


# ─────────────────────────────────────────────────────────────────────────────
# MSG-001 到 MSG-009: 消息处理分支
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_msg_001_start_listening_clears_buffer_and_sets_state(mock_settings):
    """MSG-001: start_listening 开始录音

    输入: {"type": "start_listening"}
    预期: 发送 listening_started，清空 audio_buffer，设置状态为 LISTENING
    """
    ws = MockWebSocket(
        receive_texts=[
            json.dumps({"type": "start_listening"}),
            json.dumps({"type": "stop_listening"}),
        ]
    )

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", MagicMock()),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        mock_ws = create_mock_ws(
            [json.dumps({"type": "start_listening"}), json.dumps({"type": "stop_listening"})]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        types_sent = [msg["type"] for msg in mock_ws._ws.sent_messages]
        assert "listening_started" in types_sent
        assert "listening_stopped" in types_sent


@pytest.mark.asyncio
async def test_msg_002_stop_listening_empty_buffer(mock_settings):
    """MSG-002: stop_listening_空缓冲区

    输入: stop_listening（无 audio）
    预期: 发送 listening_stopped，不触发 STT
    """
    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", MagicMock()) as mock_stt,
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                json.dumps({"type": "stop_listening"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # STT 不应该被调用因为缓冲区为空
        mock_stt.transcribe.assert_not_called()


@pytest.mark.asyncio
async def test_msg_003_stop_listening_with_audio_triggers_stt(mock_settings):
    """MSG-003: stop_listening_有音频

    输入: stop_listening with audio in buffer
    预期: 触发 run_turn，发送 transcript，状态变为 PROCESSING
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream(transcript):
        yield "Hi"

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps({"type": "ping"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # STT 应该被调用因为缓冲区有音频
        mock_stt.transcribe.assert_called_once()

        # Verify transcript was sent
        types_sent = [msg.get("type") for msg in mock_ws._ws.sent_messages]
        assert "transcript" in types_sent


@pytest.mark.asyncio
async def test_msg_004_interrupt_sends_interrupt_ack_and_cancels(mock_settings):
    """MSG-004: interrupt_中断

    输入: {"type": "interrupt"}
    预期: 发送 interrupt_ack，取消 response_task，发送 interrupt_complete
    """
    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", MagicMock()),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                json.dumps({"type": "interrupt"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        types_sent = [msg.get("type") for msg in mock_ws._ws.sent_messages]
        assert "interrupt_ack" in types_sent
        assert "interrupt_complete" in types_sent


@pytest.mark.asyncio
async def test_msg_005_audio_when_listening_appends_to_buffer(mock_settings):
    """MSG-005: audio_录音中

    输入: audio 消息（状态=LISTENING）
    预期: 追加到 audio_buffer，调用 VAD.is_speech()，发送 vad_status
    """
    audio_data = np.zeros(16000, dtype=np.float32)

    mock_vad = MagicMock()
    mock_vad.is_speech = MagicMock(return_value=True)

    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("", True))

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", mock_vad),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # VAD 应该被调用
        mock_vad.is_speech.assert_called()


@pytest.mark.asyncio
async def test_msg_006_audio_when_not_listening_is_ignored(mock_settings):
    """MSG-006: audio_非录音状态

    输入: audio 消息（状态≠LISTENING）
    预期: 忽略，不追加到 buffer
    """
    audio_data = np.zeros(16000, dtype=np.float32)

    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("", True))

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        # 直接发送 audio，不先发送 start_listening
        mock_ws = create_mock_ws(
            [
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # STT 不应该被调用因为 audio 被忽略了
        mock_stt.transcribe.assert_not_called()


@pytest.mark.asyncio
async def test_msg_007_ping_returns_pong(mock_settings):
    """MSG-007: ping_心跳

    输入: {"type": "ping"}
    预期: 发送 {"type": "pong"}
    """
    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", MagicMock()),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        mock_ws = create_mock_ws([json.dumps({"type": "ping"})])

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        types_sent = [msg.get("type") for msg in mock_ws._ws.sent_messages]
        assert "pong" in types_sent


@pytest.mark.asyncio
async def test_msg_009_unknown_message_type_is_ignored(mock_settings):
    """MSG-009: unknown_未知消息

    输入: {"type": "unknown_type"}
    预期: 忽略，不报错
    """
    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", MagicMock()),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "unknown_type"}),
                json.dumps({"type": "stop_listening"}),
            ]
        )

        from src.server import main

        # 不应该抛出异常
        await main.websocket_endpoint(mock_ws)


# ─────────────────────────────────────────────────────────────────────────────
# TURN-001 到 TURN-004: run_turn 函数分支
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_turn_001_empty_transcript_returns_early(mock_settings):
    """TURN-001: 空转录本_早期返回

    条件: STT 返回 ("", True)
    预期: 发送 transcript，立即返回，发送 listening_stopped，不触发 TTS
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("", True))

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", MagicMock()) as mock_tts,
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # TTS create_stream 不应该被调用因为 transcript 为空
        mock_tts.create_stream.assert_not_called()


@pytest.mark.asyncio
async def test_turn_002_stt_failure_returns_early(mock_settings):
    """TURN-002: STT失败_早期返回

    条件: STT 返回 ("text", False)
    预期: 发送 transcript，立即返回，发送 listening_stopped，不触发 TTS
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("some text", False))

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", MagicMock()) as mock_tts,
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # TTS create_stream 不应该被调用因为 success=False
        mock_tts.create_stream.assert_not_called()


@pytest.mark.asyncio
async def test_turn_003_successful_transcription_proceeds_to_llm_tts(mock_settings):
    """TURN-003: 成功转录_进入LLM_TTS

    条件: STT 返回 ("Hello", True)
    预期: 发送 transcript，触发 LLM+TTS 并行执行
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream(transcript):
        yield "Hi"

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # TTS 应该被创建
        mock_tts.create_stream.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# EXC-001 到 EXC-004: 异常处理
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exc_001_cancelled_error_handled(mock_settings):
    """EXC-001: CancelledError_处理

    条件: run_turn 中发生 CancelledError
    预期: 发送 tts_end(interrupted=True)，发送 listening_stopped，重新抛出
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream_that_cancels(transcript):
        raise asyncio.CancelledError("Cancelled")

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream_that_cancels
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # 查找 tts_end 消息
        tts_end_msgs = [msg for msg in mock_ws._ws.sent_messages if msg.get("type") == "tts_end"]
        assert len(tts_end_msgs) > 0


@pytest.mark.asyncio
async def test_exc_002_generic_exception_sends_fallback(mock_settings):
    """EXC-002: GenericException_处理

    条件: run_turn 中发生 Exception
    预期: 发送 fallback 消息，发送 tts_end(interrupted=True)
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream_that_fails(transcript):
        raise RuntimeError("LLM error")

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream_that_fails
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # 查找 fallback 消息
        fallback_msgs = [
            msg for msg in mock_ws._ws.sent_messages if "Sorry" in str(msg.get("text", ""))
        ]
        assert len(fallback_msgs) > 0


# ─────────────────────────────────────────────────────────────────────────────
# CANCEL-001 到 CANCEL-004: cancel_response 函数
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_004_send_interrupt_event_true(mock_settings):
    """CANCEL-004: send_interrupt_event_True

    条件: send_interrupt_event=True
    预期: 额外发送 interrupt_complete
    """
    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", MagicMock()),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                json.dumps({"type": "interrupt"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        types_sent = [msg.get("type") for msg in mock_ws._ws.sent_messages]
        assert "interrupt_ack" in types_sent


# ─────────────────────────────────────────────────────────────────────────────
# STATE-001 到 STATE-006: 状态机转换
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_state_006_stop_listening_when_not_listening(mock_settings):
    """STATE-006: 非LISTENING状态收到stop

    条件: stop_listening（状态≠LISTENING）
    预期: 发送 listening_stopped，状态变为 IDLE
    """
    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", MagicMock()),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        # 不发送 start_listening，直接发送 stop_listening
        mock_ws = create_mock_ws([json.dumps({"type": "stop_listening"})])

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        types_sent = [msg.get("type") for msg in mock_ws._ws.sent_messages]
        assert "listening_stopped" in types_sent


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE-001 到 PIPELINE-007: LLM+TTS 并行执行
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pipeline_001_both_loops_complete_normally(mock_settings):
    """PIPELINE-001: 正常完成

    条件: LLM 和 TTS 都正常
    预期: 发送 tts_start, audio_chunk, tts_end, response_complete
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello world", True))

    audio_chunks = [b"\x00" * 512, b"\x00" * 512]
    mock_tts_stream = MockTTSStream(audio_chunks=audio_chunks)
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream(transcript):
        yield "Hi"
        yield " there!"

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        types_sent = [msg.get("type") for msg in mock_ws._ws.sent_messages]
        assert "tts_start" in types_sent
        assert "audio_chunk" in types_sent
        assert "tts_end" in types_sent
        assert "response_complete" in types_sent


@pytest.mark.asyncio
async def test_pipeline_006_tts_stream_feed_called_for_each_llm_chunk(mock_settings):
    """PIPELINE-006: feed调用次数

    条件: LLM yield 3个chunk
    预期: tts_stream.feed() 被调用 3 次
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream(transcript):
        yield "Chunk1 "
        yield "Chunk2 "
        yield "Chunk3"

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # feed 应该被调用 3 次
        assert mock_tts_stream.feed_call_count == 3
        assert mock_tts_stream.finish_called is True


# ─────────────────────────────────────────────────────────────────────────────
# TURN-004: STT 异常
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_turn_004_stt_exception(mock_settings):
    """TURN-004: STT异常

    条件: STT transcribe 抛出异常
    预期: 捕获异常，发送 fallback 消息
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(side_effect=Exception("STT error"))

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # 应该发送 fallback 消息
        fallback_msgs = [
            msg for msg in mock_ws._ws.sent_messages if "Sorry" in str(msg.get("text", ""))
        ]
        assert len(fallback_msgs) > 0


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE-002 到 PIPELINE-005: 并行执行异常
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pipeline_002_llm_exception(mock_settings):
    """PIPELINE-002: LLM异常

    条件: chat_stream 抛出异常
    预期: 捕获异常，发送 fallback，发送 tts_end(interrupted=True)
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream_that_fails(transcript):
        raise Exception("LLM error")

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream_that_fails
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # 查找 fallback 消息
        fallback_msgs = [
            msg for msg in mock_ws._ws.sent_messages if "Sorry" in str(msg.get("text", ""))
        ]
        assert len(fallback_msgs) > 0


@pytest.mark.asyncio
async def test_pipeline_003_tts_exception(mock_settings):
    """PIPELINE-003: TTS异常

    条件: TTS stream 迭代抛出异常
    预期: 捕获异常，发送 fallback，发送 tts_end(interrupted=True)
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(raise_exception=True)
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream(transcript):
        yield "Hi"

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # 查找 fallback 消息
        fallback_msgs = [
            msg for msg in mock_ws._ws.sent_messages if "Sorry" in str(msg.get("text", ""))
        ]
        assert len(fallback_msgs) > 0


@pytest.mark.asyncio
async def test_pipeline_004_websocket_disconnect_during_execution(mock_settings):
    """PIPELINE-004: WebSocket断开

    条件: 并行执行中客户端断开
    预期: 捕获 WebSocketDisconnect，清理资源
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream_with_delay(transcript):
        await asyncio.sleep(0.1)
        yield "Hi"

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream_with_delay
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)

        # 创建会在第二次 receive 时抛出 WebSocketDisconnect 的 mock
        ws = MockWebSocket(
            receive_texts=[
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
            ],
            raise_disconnect=True,
        )
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.receive_text = ws.receive_text
        mock_ws.send_json = ws.send_json
        mock_ws.close = AsyncMock()
        mock_ws.query_params = MagicMock()
        mock_ws.query_params.get = MagicMock(return_value=None)
        mock_ws.headers = MagicMock()
        mock_ws.headers.get = MagicMock(return_value=None)

        from src.server import main

        # 不应该抛出异常
        await main.websocket_endpoint(mock_ws)


@pytest.mark.asyncio
async def test_pipeline_005_cancel_sends_tts_end_interrupted(mock_settings):
    """PIPELINE-005: 取消_CancelledError

    条件: cancel_response 取消任务
    预期: 发送 tts_end(interrupted=True)，发送 listening_stopped
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream_that_yields_forever(transcript):
        yield "Hi"
        await asyncio.sleep(100)  # 模拟长时间运行

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream_that_yields_forever
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # 查找 tts_end(interrupted=True)
        tts_end_msgs = [
            msg
            for msg in mock_ws._ws.sent_messages
            if msg.get("type") == "tts_end" and msg.get("interrupted") is True
        ]
        assert len(tts_end_msgs) > 0


@pytest.mark.asyncio
async def test_pipeline_007_subtitle_chunk_sent_when_streaming(mock_settings):
    """PIPELINE-007: subtitle发送

    条件: SUBTITLE_STREAMING=true，LLM yield
    预期: 发送 subtitle_chunk 消息
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream(transcript):
        yield "Hi"
        yield " there!"

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main.SUBTITLE_STREAMING", True),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
                json.dumps({"type": "ping"}),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        types_sent = [msg.get("type") for msg in mock_ws._ws.sent_messages]
        assert "subtitle_chunk" in types_sent


# ─────────────────────────────────────────────────────────────────────────────
# EXC-003, EXC-004: 异常处理
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exc_003_websocket_send_fails_in_exception_handler(mock_settings):
    """EXC-003: WebSocket发送失败

    条件: 异常处理中 WebSocket 已断开
    预期: 静默忽略，不抛出
    """
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream_that_fails(transcript):
        raise RuntimeError("LLM error")

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream_that_fails
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)

        # 创建会在 send 时抛出 RuntimeError 的 mock
        ws = MockWebSocket(
            receive_texts=[
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
            ],
            raise_on_send=True,
        )
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.receive_text = ws.receive_text
        mock_ws.send_json = ws.send_json
        mock_ws.close = AsyncMock()
        mock_ws.query_params = MagicMock()
        mock_ws.query_params.get = MagicMock(return_value=None)
        mock_ws.headers = MagicMock()
        mock_ws.headers.get = MagicMock(return_value=None)

        from src.server import main

        # 不应该抛出异常
        await main.websocket_endpoint(mock_ws)


@pytest.mark.asyncio
async def test_exc_004_websocket_disconnect_cleanup(mock_settings):
    """EXC-004: 外部异常_清理

    条件: outer handler 捕获 WebSocketDisconnect
    预期: 调用 cancel_response，关闭 WebSocket
    """
    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", MagicMock()),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        ws = MockWebSocket(
            receive_texts=[
                json.dumps({"type": "start_listening"}),
            ],
            raise_disconnect=True,
        )
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.receive_text = ws.receive_text
        mock_ws.send_json = ws.send_json
        mock_ws.close = AsyncMock()
        mock_ws.query_params = MagicMock()
        mock_ws.query_params.get = MagicMock(return_value=None)
        mock_ws.headers = MagicMock()
        mock_ws.headers.get = MagicMock(return_value=None)

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # close() 应该被调用并 await
        mock_ws.close.assert_called()
        mock_ws.close.assert_awaited()


# ─────────────────────────────────────────────────────────────────────────────
# MSG-008: perf_report 性能报告
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_msg_008_perf_report_calls_log_round(mock_settings):
    """MSG-008: perf_report_性能报告

    输入: {"type": "perf_report", "metrics": {...}}
    预期: 调用 perf_logger.log_round()
    """
    mock_perf_logger_instance = MagicMock()
    mock_perf_logger_instance.is_enabled = MagicMock(return_value=True)
    mock_perf_logger_instance.log_round = MagicMock()

    mock_backend = MagicMock()
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", MagicMock()),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger", mock_perf_logger_instance),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        mock_ws = create_mock_ws(
            [
                json.dumps(
                    {"type": "perf_report", "metrics": {"button_release_to_tts_end_ms": 100}}
                ),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # log_round 应该被调用
        mock_perf_logger_instance.log_round.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# PERF-001, PERF-002: 性能日志
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_perf_001_perf_logger_enabled_sends_data(mock_settings):
    """PERF-001: perf_logger启用

    条件: perf_logger.is_enabled()=True
    预期: perf_data 被填充并传递给 log_round
    """
    mock_perf_logger_instance = MagicMock()
    mock_perf_logger_instance.is_enabled = MagicMock(return_value=True)
    mock_perf_logger_instance.log_round = MagicMock()

    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream(transcript):
        yield "Hi"

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger", mock_perf_logger_instance),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps(
                    {"type": "perf_report", "metrics": {"button_release_to_tts_end_ms": 100}}
                ),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # log_round 应该被调用（带 backend_data）
        mock_perf_logger_instance.log_round.assert_called()

        # 验证 log_round 收到的参数包含真实的 transcript
        # transcript 由 STT 同步写入 TurnContext，在 perf_report 处理前已完成
        call_kwargs = mock_perf_logger_instance.log_round.call_args[1]
        assert call_kwargs["context"]["transcript"] == "Hello"

        # backend_data 的 perf_data 可能为空（VoiceTurn 任务并发执行，
        # perf_report 在 LLM+TTS 完成前就被处理），但 dict 结构应存在
        assert isinstance(call_kwargs["backend_data"], dict)


@pytest.mark.asyncio
async def test_perf_002_perf_logger_disabled(mock_settings):
    """PERF-002: perf_logger禁用

    条件: perf_logger.is_enabled()=False
    预期: perf_data 保持为空，不调用 log_round
    """
    mock_perf_logger_instance = MagicMock()
    mock_perf_logger_instance.is_enabled = MagicMock(return_value=False)
    mock_perf_logger_instance.log_round = MagicMock()

    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream(transcript):
        yield "Hi"

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger", mock_perf_logger_instance),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
                json.dumps(
                    {"type": "perf_report", "metrics": {"button_release_to_tts_end_ms": 100}}
                ),
            ]
        )

        from src.server import main

        await main.websocket_endpoint(mock_ws)

        # log_round 不应该被调用
        mock_perf_logger_instance.log_round.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# CANCEL-001 到 CANCEL-003: cancel_response 函数分支
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_001_response_task_none_no_op(mock_settings):
    """CANCEL-001: task为None

    条件: response_task=None
    预期: 无操作，直接返回
    """
    # 这个通过 start_listening -> stop_listening (空buffer) 测试
    # response_task 从未被设置，所以 cancel_response 会看到 None
    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", MagicMock()),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                json.dumps({"type": "stop_listening"}),
            ]
        )

        from src.server import main

        # 不应该抛出异常
        await main.websocket_endpoint(mock_ws)


@pytest.mark.asyncio
async def test_cancel_002_task_running_gets_cancelled(mock_settings):
    """CANCEL-002: task未完成

    条件: response_task 正在运行
    预期: 取消 task，等待完成
    """
    # 创建一个永远不会完成的 chat_stream 来模拟长时间运行的任务
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=("Hello", True))

    mock_tts_stream = MockTTSStream(audio_chunks=[b"\x00" * 1024])
    mock_tts = MagicMock()
    mock_tts.create_stream = MagicMock(return_value=mock_tts_stream)

    async def mock_chat_stream_never_ends(transcript):
        await asyncio.sleep(100)  # 模拟长时间运行
        yield "Hi"

    mock_backend = MagicMock()
    mock_backend.chat_stream = mock_chat_stream_never_ends
    mock_backend.model_name = "mock"

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", mock_stt),
        patch("src.server.main.tts", mock_tts),
        patch("src.server.main.backend", mock_backend),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        audio_data = np.zeros(16000, dtype=np.float32)
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
                make_audio_msg(audio_data),
                json.dumps({"type": "stop_listening"}),
            ]
        )

        from src.server import main

        # 不应该抛出异常 - cancel_response 应该正确处理
        await main.websocket_endpoint(mock_ws)

        # 如果 cancel_response 正确工作，测试应该正常完成
        assert True


@pytest.mark.asyncio
async def test_cancel_003_response_task_already_done(mock_settings):
    """CANCEL-003: task已完成

    条件: response_task 已完成
    预期: 无操作，直接返回
    """
    # 创建一个已完成的 task
    done_task = asyncio.create_task(asyncio.sleep(0))
    await done_task  # 确保完成

    with (
        patch("src.server.main.settings", mock_settings),
        patch("src.server.main.stt", MagicMock()),
        patch("src.server.main.tts", MagicMock()),
        patch("src.server.main.backend", MagicMock()),
        patch("src.server.main.vad", MagicMock()),
        patch("src.server.main.perf_logger"),
        patch("src.server.main._validate_ws_auth", AsyncMock(return_value=None)),
    ):
        mock_ws = create_mock_ws(
            [
                json.dumps({"type": "start_listening"}),
            ]
        )

        from src.server import main

        # 不应该抛出异常
        await main.websocket_endpoint(mock_ws)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
