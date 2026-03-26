"""
Agent streaming synthesis for LangChain agents.

Handles LangChain agent event streaming and TTS audio generation in parallel,
providing non-blocking tool execution with continuous audio output.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, AsyncGenerator

from loguru import logger

if TYPE_CHECKING:
    from .base import BaseAgent
    from .events import AgentEvent, StreamChunkEvent
    from turn_context import TurnContext


@dataclass
class AgentSynthesisConfig:
    """Configuration for agent TTS synthesis."""

    sample_rate: int = 24000
    subtitle_streaming: bool = True


@dataclass
class AgentSynthesisMetrics:
    """Performance metrics for agent synthesis."""

    llm_ttft_ms: Optional[float] = None
    llm_gen_ms: Optional[float] = None
    tts_ttfa_ms: Optional[float] = None
    tts_total_ms: Optional[float] = None
    audio_chunks_sent: int = 0


@dataclass
class AgentSynthesisResult:
    """Result of agent synthesis execution."""

    full_response: str
    metrics: AgentSynthesisMetrics


class AgentStreamingSynthesis:
    """
    Orchestrates LangChain agent events and TTS streaming in parallel.

    Unlike StreamingSynthesis which uses LLM.chat_stream(), this class
    handles agent.astream() which yields AgentEvent objects including
    StreamChunkEvent, ToolStartEvent, and ToolCompleteEvent.

    Usage:
        synthesis = AgentStreamingSynthesis(
            agent=agent,
            tts=tts,
            websocket=ws,
            config=AgentSynthesisConfig(),
            turn_context=turn_context,
        )
        result = await synthesis.run(transcript)
    """

    def __init__(
        self,
        agent: "BaseAgent",
        tts,
        websocket,
        config: AgentSynthesisConfig = AgentSynthesisConfig(),
        turn_context: Optional["TurnContext"] = None,
    ):
        self._agent = agent
        self._tts = tts
        self._ws = websocket
        self._config = config
        self._turn_context = turn_context

    async def run(self, transcript: str) -> AgentSynthesisResult:
        """
        Run agent synthesis: agent yields events while TTS streams audio.

        Args:
            transcript: The STT transcript to send to agent

        Returns:
            AgentSynthesisResult with full response and metrics
        """
        full_response = ""
        tts_stream_holder = [self._tts.create_stream()]

        metrics = AgentSynthesisMetrics()
        t_start = time.perf_counter()
        t_llm_first: Optional[float] = None
        t_llm_end: Optional[float] = None
        t_tts_first: Optional[float] = None
        tts_start_time = asyncio.get_running_loop().time()
        audio_chunks_sent = 0

        SENTENCE_ENDINGS = set('。！？；：""（）.,!?;:"\'()')

        async def agent_feed_loop():
            """Agent produces events → StreamChunkEvent text → buffer by sentence → feed to TTS."""
            nonlocal full_response, t_llm_first, t_llm_end
            import datetime

            sentence_buffer = ""
            need_new_stream = False
            try:
                async for event in self._agent.astream(transcript):
                    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

                    from .events import StreamChunkEvent, ToolStartEvent, ToolCompleteEvent

                    if isinstance(event, StreamChunkEvent):
                        token = event.text
                        logger.info(f"[{now}] 🤖 Agent chunk received: {token!r}")

                        if not t_llm_first:
                            t_llm_first = time.perf_counter()

                        full_response += token
                        if self._config.subtitle_streaming:
                            await self._ws.send_subtitle_chunk(token)

                        if need_new_stream:
                            tts_stream_holder[0] = self._tts.create_stream()
                            tts_stream_holder[0]._ensure_connected()
                            need_new_stream = False

                        sentence_buffer += token

                        if token in SENTENCE_ENDINGS:
                            tts_stream_holder[0].feed(sentence_buffer)
                            sentence_buffer = ""
                            logger.info(f"[{now}] 🔊 Sentence end detected, finishing TTS stream")
                            tts_stream_holder[0].finish()
                            need_new_stream = True

                    elif isinstance(event, ToolStartEvent):
                        tool_name = event.tool_name
                        logger.info(f"[{now}] 🔧 Tool start: {tool_name}")
                        if sentence_buffer:
                            tts_stream_holder[0].feed(sentence_buffer)
                            sentence_buffer = ""
                        tts_stream_holder[0].finish()
                        need_new_stream = True

                    elif isinstance(event, ToolCompleteEvent):
                        tool_name = event.tool_name
                        logger.info(f"[{now}] 🔧 Tool complete: {tool_name}")

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

        await asyncio.gather(agent_feed_loop(), tts_consume_loop())

        tts_total_time = asyncio.get_running_loop().time() - tts_start_time
        logger.info(
            "🔊 Agent synthesis complete: {} chunks, total {:.1f}ms",
            audio_chunks_sent,
            tts_total_time * 1000,
        )

        metrics.llm_ttft_ms = (t_llm_first - t_start) * 1000 if t_llm_first else None
        metrics.llm_gen_ms = (t_llm_end - t_llm_first) * 1000 if t_llm_first and t_llm_end else None
        metrics.tts_total_ms = tts_total_time * 1000
        metrics.audio_chunks_sent = audio_chunks_sent

        return AgentSynthesisResult(full_response=full_response, metrics=metrics)
