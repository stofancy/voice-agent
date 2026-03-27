"""
Tests for AgentStreamingSynthesis.

Verifies that agent events are properly streamed to TTS without blocking.
"""

import pytest

try:
    from src.server.agent import AgentStreamingSynthesis, AgentSynthesisConfig, LANGCHAIN_AVAILABLE
except ImportError:
    LANGCHAIN_AVAILABLE = False


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestAgentSynthesisConfig:
    """Tests for AgentSynthesisConfig dataclass."""

    def test_default_config(self):
        """Default config has expected values."""
        config = AgentSynthesisConfig()

        assert config.sample_rate == 24000
        assert config.subtitle_streaming is True

    def test_custom_config(self):
        """Custom config values are preserved."""
        config = AgentSynthesisConfig(
            sample_rate=16000,
            subtitle_streaming=False,
        )

        assert config.sample_rate == 16000
        assert config.subtitle_streaming is False


@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="langchain-core not installed")
class TestAgentStreamingSynthesis:
    """Tests for AgentStreamingSynthesis class."""

    def test_initialization(self):
        """Synthesis initializes with required components."""
        mock_agent = object()
        mock_tts = object()
        mock_ws = object()

        synthesis = AgentStreamingSynthesis(
            agent=mock_agent,
            tts=mock_tts,
            websocket=mock_ws,
        )

        assert synthesis._agent is mock_agent
        assert synthesis._tts is mock_tts
        assert synthesis._ws is mock_ws
        assert synthesis._turn_context is None

    def test_initialization_with_config(self):
        """Synthesis initializes with custom config."""
        mock_agent = object()
        mock_tts = object()
        mock_ws = object()
        config = AgentSynthesisConfig(sample_rate=16000)

        synthesis = AgentStreamingSynthesis(
            agent=mock_agent,
            tts=mock_tts,
            websocket=mock_ws,
            config=config,
        )

        assert synthesis._config.sample_rate == 16000

    def test_initialization_with_turn_context(self):
        """Synthesis initializes with turn context."""
        from src.server.turn_context import TurnContext

        mock_agent = object()
        mock_tts = object()
        mock_ws = object()
        tc = TurnContext()

        synthesis = AgentStreamingSynthesis(
            agent=mock_agent,
            tts=mock_tts,
            websocket=mock_ws,
            turn_context=tc,
        )

        assert synthesis._turn_context is tc
