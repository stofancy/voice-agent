"""
Unit tests for StreamController.
"""

import pytest


try:
    from src.server.agent import StreamController, LANGCHAIN_AVAILABLE
except ImportError:
    LANGCHAIN_AVAILABLE = False
    StreamController = object


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestStreamController:
    """Tests for StreamController callback handler."""

    def test_initialization(self):
        """StreamController initializes with correct defaults."""
        sc = StreamController()

        assert sc.is_cancelled is False
        assert sc.tts_callback is None
        assert sc.ws_callback is None

    def test_initialization_with_callbacks(self):
        """StreamController accepts optional callbacks."""

        def tts_cb(x):
            pass

        def ws_cb(x):
            pass

        sc = StreamController(tts_callback=tts_cb, ws_callback=ws_cb)

        assert sc.tts_callback == tts_cb
        assert sc.ws_callback == ws_cb

    def test_reset(self):
        """reset() clears state."""
        sc = StreamController()
        sc.is_cancelled = True
        sc._current_tool = "test_tool"

        sc.reset()

        assert sc.is_cancelled is False
        assert sc._current_tool is None

    def test_check_cancelled_false(self):
        """check_cancelled returns False when not cancelled."""
        sc = StreamController()
        sc.is_cancelled = False

        assert sc.check_cancelled() is False

    def test_check_cancelled_true(self):
        """check_cancelled returns True when cancelled."""
        sc = StreamController()
        sc.is_cancelled = True

        assert sc.check_cancelled() is True

    def test_cancelled_tool_start_skipped(self):
        """on_tool_start does nothing when cancelled."""
        sc = StreamController()
        sc.is_cancelled = True

        sc.on_tool_start(serialized={"name": "test"}, input_str="input")

        assert sc._current_tool is None

    def test_cancelled_tool_end_skipped(self):
        """on_tool_end does nothing when cancelled."""
        sc = StreamController()
        sc.is_cancelled = True

        sc.on_tool_end(output="result")

        assert sc._current_tool is None
