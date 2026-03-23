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

    sample_rate: int = 24000
    subtitle_streaming: bool = True


@dataclass
class SynthesisMetrics:
    """Performance metrics collected during synthesis execution."""

    llm_ttft_ms: Optional[float] = None  # Time to first token
    llm_gen_ms: Optional[float] = None  # Total LLM generation time
    tts_ttfa_ms: Optional[float] = None  # Time to first audio
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
        t_start = time.perf_counter()
        t_llm_first: Optional[float] = None
        t_llm_end: Optional[float] = None
        t_tts_first: Optional[float] = None
        tts_start_time = asyncio.get_running_loop().time()
        audio_chunks_sent = 0

        async def llm_feed_loop():
            """LLM produces tokens → feed to TTS → send subtitles."""
            nonlocal full_response, t_llm_first, t_llm_end
            import datetime

            tts_finished = False
            last_chunk_time = asyncio.get_running_loop().time()
            try:
                async for chunk in self._llm.chat_stream(transcript):
                    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

                    current_time = asyncio.get_running_loop().time()
                    time_since_last_chunk = current_time - last_chunk_time

                    if time_since_last_chunk > 5.0 and not tts_finished:
                        logger.info(
                            f"[{now}] 🔊 LLM pause detected ({time_since_last_chunk:.1f}s), finishing TTS stream"
                        )
                        tts_stream.finish()
                        tts_finished = True

                    last_chunk_time = current_time

                    logger.info(
                        f"[{now}] 🤖 LLM chunk received: {chunk!r}, full_response so far: {full_response!r}"
                    )
                    if chunk == "[TOOL_CALL]":
                        logger.info(f"[{now}] 🔊 Tool call detected, finishing TTS stream")
                        tts_stream.finish()
                        tts_finished = True
                        continue
                    full_response += chunk
                    if t_llm_first is None:
                        t_llm_first = time.perf_counter()
                    if self._config.subtitle_streaming:
                        await self._ws.send_subtitle_chunk(chunk)
                    tts_stream.feed(chunk)
            finally:
                now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                logger.info(f"[{now}] 🔊 LLM feed loop ending, calling finish()")
                if not tts_finished:
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

            try:
                async for audio_chunk in tts_stream:
                    import datetime

                    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    logger.info(f"[{now}] 🔊 TTS audio chunk received: {len(audio_chunk)} bytes")
                    if self._turn_context is not None and self._turn_context.is_cancelled():
                        logger.warning("🔊 TTS consume loop interrupted by cancellation")
                        break

                    buffer.extend(audio_chunk)

                    if not first_chunk_received:
                        first_chunk_received = True
                        t_tts_first = time.perf_counter()
                        if t_llm_first is not None:
                            metrics.tts_ttfa_ms = (t_tts_first - t_llm_first) * 1000

                    logger.info(f"[{now}] 🔊 Sending audio to client: {len(buffer)} bytes")
                    await self._ws.send_audio_chunk(bytes(buffer), self._config.sample_rate)
                    audio_chunks_sent += 1
                    buffer = bytearray()

                if buffer:
                    await self._ws.send_audio_chunk(bytes(buffer), self._config.sample_rate)
                    audio_chunks_sent += 1
                logger.info(f"🔊 TTS consume loop finished, sent {audio_chunks_sent} chunks")

            except asyncio.CancelledError:
                logger.warning("🔊 TTS consume loop cancelled")
                raise
            except Exception as e:
                logger.error(f"🔊 TTS consume loop error: {e}")
                raise
            except Exception as e:
                logger.error(f"🔊 TTS consume loop error: {e}")
                raise

        # Run both loops in parallel
        await asyncio.gather(llm_feed_loop(), tts_consume_loop())

        # Calculate metrics
        tts_total_time = asyncio.get_running_loop().time() - tts_start_time
        logger.info(
            "🔊 TTS complete: {} chunks, total {:.1f}ms", audio_chunks_sent, tts_total_time * 1000
        )

        metrics.llm_ttft_ms = (t_llm_first - t_start) * 1000 if t_llm_first else None
        metrics.llm_gen_ms = (t_llm_end - t_llm_first) * 1000 if t_llm_first and t_llm_end else None
        metrics.tts_total_ms = tts_total_time * 1000
        metrics.audio_chunks_sent = audio_chunks_sent

        return SynthesisResult(full_response=full_response, metrics=metrics)
