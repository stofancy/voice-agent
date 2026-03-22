"""
Streaming synthesis orchestration.

Handles LLM token generation and TTS streaming in parallel,
providing low-latency voice response.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from turn_context import TurnContext


@dataclass
class SynthesisConfig:
    """Configuration for TTS buffering."""
    data_buffer_size: int = 8192
    time_buffer_seconds: float = 0.1
    sample_rate: int = 24000
    subtitle_streaming: bool = True


@dataclass
class SynthesisMetrics:
    """Performance metrics collected during synthesis execution."""
    llm_ttft_ms: Optional[float] = None  # Time to first token
    llm_gen_ms: Optional[float] = None   # Total LLM generation time
    tts_ttfa_ms: Optional[float] = None   # Time to first audio
    tts_total_ms: Optional[float] = None  # Total TTS time
    audio_chunks_sent: int = 0


@dataclass
class SynthesisResult:
    """Result of a synthesis execution."""
    full_response: str
    metrics: SynthesisMetrics


class StreamingSynthesis:
    """
    Orchestrates LLM feed and TTS consume in parallel.

    Usage:
        synthesis = StreamingSynthesis(
            llm=backend,
            tts=tts,
            websocket=ws,
            config=SynthesisConfig(),
        )
        result = await synthesis.run(transcript)
    """

    def __init__(
        self,
        llm,  # BaseLLM
        tts,  # BaseTTS
        websocket,  # WebSocketConnection
        config: SynthesisConfig = SynthesisConfig(),
        turn_context: Optional["TurnContext"] = None,
    ):
        self._llm = llm
        self._tts = tts
        self._ws = websocket
        self._config = config
        self._turn_context = turn_context

    async def run(self, transcript: str) -> SynthesisResult:
        """
        Run the synthesis: LLM generates tokens while TTS streams audio.

        Args:
            transcript: The STT transcript to send to LLM

        Returns:
            SynthesisResult with full response and metrics
        """
        full_response = ""
        tts_stream = self._tts.create_stream()

        # Metrics tracking
        metrics = SynthesisMetrics()
        t_llm_first: Optional[float] = None
        t_llm_end: Optional[float] = None
        t_tts_first: Optional[float] = None
        tts_start_time = asyncio.get_event_loop().time()
        audio_chunks_sent = 0

        async def llm_feed_loop():
            """LLM produces tokens → feed to TTS → send subtitles."""
            nonlocal full_response, t_llm_first, t_llm_end
            try:
                async for chunk in self._llm.chat_stream(transcript):
                    full_response += chunk
                    if t_llm_first is None:
                        t_llm_first = time.perf_counter()
                    if self._config.subtitle_streaming:
                        await self._ws.send_subtitle_chunk(chunk)
                    tts_stream.feed(chunk)
            finally:
                tts_stream.finish()
                t_llm_end = time.perf_counter()

        async def tts_consume_loop():
            """TTS audio streaming → buffering → send to client."""
            nonlocal t_tts_first, t_llm_end, audio_chunks_sent, tts_start_time
            logger.info("🔊 TTS consume loop started")
            tts_stream._ensure_connected()
            logger.info("🔊 TTS stream ensured connected")

            buffer = bytearray()
            first_chunk_received = False
            buffer_start_time: Optional[float] = None

            try:
                async for audio_chunk in tts_stream:
                    # Check for cancellation
                    if self._turn_context is not None and self._turn_context.is_cancelled():
                        logger.warning("🔊 TTS consume loop interrupted by cancellation")
                        break

                    buffer.extend(audio_chunk)

                    if not first_chunk_received:
                        first_chunk_received = True
                        t_tts_first = time.perf_counter()
                        if t_llm_end is not None:
                            metrics.tts_ttfa_ms = (t_tts_first - t_llm_end) * 1000
                        buffer_start_time = asyncio.get_event_loop().time()
                        logger.info(f"🔊 TTS first chunk received, buffering {self._config.time_buffer_seconds}s...")

                    current_time = asyncio.get_event_loop().time()
                    time_buffer_elapsed = (
                        (current_time - buffer_start_time) if buffer_start_time is not None else 0
                    )

                    if (
                        len(buffer) >= self._config.data_buffer_size
                        and time_buffer_elapsed >= self._config.time_buffer_seconds
                    ):
                        await self._ws.send_audio_chunk(
                            bytes(buffer), self._config.sample_rate
                        )
                        audio_chunks_sent += 1
                        logger.debug(
                            "🔊 sent chunk #{}: {} bytes, latency {:.1f}ms",
                            audio_chunks_sent,
                            len(buffer),
                            (current_time - tts_start_time) * 1000,
                        )
                        buffer = bytearray()
                        buffer_start_time = asyncio.get_event_loop().time()

                if buffer:
                    await self._ws.send_audio_chunk(
                        bytes(buffer), self._config.sample_rate
                    )
                    audio_chunks_sent += 1
                logger.info(f"🔊 TTS consume loop finished, sent {audio_chunks_sent} chunks")

            except asyncio.CancelledError:
                logger.warning("🔊 TTS consume loop cancelled")
                raise
            except Exception as e:
                logger.error(f"🔊 TTS consume loop error: {e}")
                raise

        # Run both loops in parallel
        await asyncio.gather(llm_feed_loop(), tts_consume_loop())

        # Calculate metrics
        tts_total_time = asyncio.get_event_loop().time() - tts_start_time
        logger.info("🔊 TTS complete: {} chunks, total {:.1f}ms", audio_chunks_sent, tts_total_time * 1000)

        metrics.llm_ttft_ms = (t_llm_first - t_llm_end) * 1000 if t_llm_first and t_llm_end else None
        metrics.llm_gen_ms = (t_llm_end - t_llm_first) * 1000 if t_llm_first and t_llm_end else None
        metrics.tts_total_ms = tts_total_time * 1000
        metrics.audio_chunks_sent = audio_chunks_sent

        return SynthesisResult(full_response=full_response, metrics=metrics)
