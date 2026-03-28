"""
Tests for interruption handling.

Verifies that TurnContext cancellation and StreamController cancellation work correctly.
T030: Test: speak during tool execution, verify new request processed
"""

import asyncio
import pytest

try:
    from src.server.agent import LANGCHAIN_AVAILABLE
except ImportError:
    LANGCHAIN_AVAILABLE = False


class TestTurnContextCancellation:
    """Tests for TurnContext cancellation mechanism."""

    def test_initial_state_not_cancelled(self):
        """Initial state is not cancelled."""
        from src.server.turn_context import TurnContext

        tc = TurnContext()
        assert tc.is_cancelled() is False

    def test_cancel_sets_flag(self):
        """cancel() sets the cancelled flag."""
        from src.server.turn_context import TurnContext

        tc = TurnContext()
        tc.cancel()
        assert tc.is_cancelled() is True

    def test_reset_clears_flag(self):
        """reset() clears the cancelled flag."""
        from src.server.turn_context import TurnContext

        tc = TurnContext()
        tc.cancel()
        assert tc.is_cancelled() is True
        tc.reset()
        assert tc.is_cancelled() is False

    def test_reset_clears_all_fields(self):
        """reset() clears all fields to initial state."""
        from src.server.turn_context import TurnContext

        tc = TurnContext()
        tc.transcript = "test transcript"
        tc.full_response = "test response"
        tc.perf_data = {"test": "data"}
        tc.reset()

        assert tc.transcript == ""
        assert tc.full_response == ""
        assert tc.perf_data == {}

    def test_cancel_uses_asyncio_event(self):
        """Cancellation uses asyncio.Event for proper async signaling."""
        from src.server.turn_context import TurnContext

        tc = TurnContext()
        assert isinstance(tc.cancelled, asyncio.Event)

    @pytest.mark.asyncio
    async def test_wait_for_cancellation(self):
        """Can wait for cancellation using asyncio.Event."""
        from src.server.turn_context import TurnContext

        tc = TurnContext()

        async def cancel_after_delay():
            await asyncio.sleep(0.1)
            tc.cancel()

        async def wait_for_cancel():
            await tc.cancelled.wait()
            return True

        result = await asyncio.gather(
            wait_for_cancel(),
            cancel_after_delay(),
        )
        assert result == [True, None]

    def test_multiple_cancels_dont_block(self):
        """Multiple cancel() calls don't cause issues."""
        from src.server.turn_context import TurnContext

        tc = TurnContext()
        tc.cancel()
        tc.cancel()
        tc.cancel()
        assert tc.is_cancelled() is True


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestStreamControllerCancellation:
    """Tests for StreamController cancellation handling."""

    def test_initial_state_not_cancelled(self):
        """Initial state is not cancelled."""
        from src.server.agent.stream_controller import StreamController

        controller = StreamController()
        assert controller.is_cancelled is False
        assert controller.check_cancelled() is False

    def test_reset_clears_cancelled_flag(self):
        """reset() clears the cancelled flag."""
        from src.server.agent.stream_controller import StreamController

        controller = StreamController()
        controller.is_cancelled = True
        controller.reset()
        assert controller.is_cancelled is False

    def test_check_cancelled_returns_flag_value(self):
        """check_cancelled() returns the is_cancelled flag value."""
        from src.server.agent.stream_controller import StreamController

        controller = StreamController()
        assert controller.check_cancelled() is False

        controller.is_cancelled = True
        assert controller.check_cancelled() is True

    def test_on_llm_start_respects_cancellation(self):
        """on_llm_start skips callback when cancelled."""
        from src.server.agent.stream_controller import StreamController

        controller = StreamController()
        controller.is_cancelled = True

        callback_called = []
        controller.tts_callback = lambda x: callback_called.append(x)

        controller.on_llm_start({}, ["prompt"])
        assert len(callback_called) == 0

    def test_on_llm_new_token_respects_cancellation(self):
        """on_llm_new_token skips callback when cancelled."""
        from src.server.agent.stream_controller import StreamController

        controller = StreamController()
        controller.is_cancelled = True

        callback_called = []
        controller.tts_callback = lambda x: callback_called.append(x)

        controller.on_llm_new_token("test token")
        assert len(callback_called) == 0

    def test_on_tool_start_respects_cancellation(self):
        """on_tool_start returns early when cancelled."""
        from src.server.agent.stream_controller import StreamController

        controller = StreamController()
        controller.is_cancelled = True

        callback_called = []
        controller.tts_callback = lambda x: callback_called.append(x)

        controller.on_tool_start({"name": "test_tool"}, "input")
        assert len(callback_called) == 0

    def test_on_tool_end_respects_cancellation(self):
        """on_tool_end returns early when cancelled."""
        from src.server.agent.stream_controller import StreamController

        controller = StreamController()
        controller.is_cancelled = True
        controller._current_tool = "test_tool"

        callback_called = []
        controller.tts_callback = lambda x: callback_called.append(x)

        controller.on_tool_end("output")
        assert len(callback_called) == 0

    def test_emit_progress_respects_cancellation(self):
        """emit_progress skips callback when cancelled."""
        import asyncio
        from src.server.agent.stream_controller import StreamController

        controller = StreamController()
        controller.is_cancelled = True

        callback_called = []
        controller.tts_callback = lambda x: callback_called.append(x)

        async def test():
            await controller.emit_progress("test")
            return len(callback_called)

        result = asyncio.get_event_loop().run_until_complete(test())
        assert result == 0


class TestVoiceTurnInterruptionFallback:
    """Tests for VoiceTurn interruption fallback text."""

    def test_fallback_text_defined_in_exception_handler(self):
        """Verify fallback text is sent on CancelledError."""
        import ast

        source_file = "src/server/voice_turn.py"

        with open(source_file) as f:
            source = f.read()

        tree = ast.parse(source)

        fallback_text_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                is_cancelled_error = False
                if node.type and isinstance(node.type, ast.Attribute):
                    if node.type.attr == "CancelledError":
                        is_cancelled_error = True
                elif node.type and hasattr(node.type, "id") and node.type.id == "CancelledError":
                    is_cancelled_error = True

                if is_cancelled_error:
                    handler_source = ast.get_source_segment(source, node)
                    if handler_source and "Sorry, let me start over" in handler_source:
                        fallback_text_found = True

        assert fallback_text_found, (
            "Fallback text 'Sorry, let me start over' not found in CancelledError handler"
        )
