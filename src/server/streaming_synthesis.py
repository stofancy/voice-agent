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
        tts_stream_holder = [self._tts.create_stream()]

        # Metrics tracking
        metrics = SynthesisMetrics()
        t_start = time.perf_counter()
        t_llm_first: Optional[float] = None
        t_llm_end: Optional[float] = None
        t_tts_first: Optional[float] = None
        tts_start_time = asyncio.get_running_loop().time()
        audio_chunks_sent = 0

        SENTENCE_ENDINGS = set('。！？；：""（）.,!?;:"\'()')

        async def llm_feed_loop():
            """LLM produces tokens → buffer by sentence → feed to TTS."""
            nonlocal full_response, t_llm_first, t_llm_end
            import datetime

            sentence_buffer = ""
            need_new_stream = False
            try:
                async for chunk in self._llm.chat_stream(transcript):
                    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

                    logger.info(f"[{now}] 🤖 LLM chunk received: {chunk!r}")
                    if chunk == "[TOOL_CALL]":
                        logger.info(f"[{now}] 🔊 Tool call detected, finishing current sentence")
                        if sentence_buffer:
                            tts_stream_holder[0].feed(sentence_buffer)
                            sentence_buffer = ""
                        tts_stream_holder[0].finish()
                        need_new_stream = True
                        continue
                    full_response += chunk
                    if t_llm_first is None:
                        t_llm_first = time.perf_counter()
                    if self._config.subtitle_streaming:
                        await self._ws.send_subtitle_chunk(chunk)

                    if need_new_stream:
                        tts_stream_holder[0] = tts_factory.create_stream()
                        tts_stream_holder[0]._ensure_connected()
                        need_new_stream = False

                    sentence_buffer += chunk

                    if chunk in SENTENCE_ENDINGS:
                        tts_stream_holder[0].feed(sentence_buffer)
                        sentence_buffer = ""
                        logger.info(f"[{now}] 🔊 Sentence end detected, finishing TTS stream")
                        tts_stream_holder[0].finish()
                        need_new_stream = True

                if sentence_buffer:
                    tts_stream_holder[0].feed(sentence_buffer)
                    sentence_buffer = ""
            finally:
                if sentence_buffer:
                    tts_stream_holder[0].feed(sentence_buffer)
                    sentence_buffer = ""
                tts_stream_holder[0].finish()
                t_llm_end = time.perf_counter()

        async def tts_consume_loop():
            """TTS audio streaming → buffering → send to client."""
            nonlocal t_tts_first, t_llm_end, audio_chunks_sent, tts_start_time
            logger.info("🔊 TTS consume loop started")
            tts_stream_holder[0]._ensure_connected()
            logger.info("🔊 TTS stream ensured connected")

            buffer = bytearray()
            first_chunk_received = False

            try:
                async for audio_chunk in tts_stream_holder[0]:
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
