"""
Voice turn orchestration.

Handles a complete voice turn: STT → StreamingSynthesis/AgentStreamingSynthesis → WebSocket messages.
"""

import asyncio
from typing import TYPE_CHECKING, Optional

import numpy as np
from loguru import logger

from .connection import ConnectionState, ConnectionStateMachine, WebSocketConnection
from .streaming_synthesis import StreamingSynthesis, SynthesisConfig

if TYPE_CHECKING:
    from .turn_context import TurnContext
    from .agent.base import BaseAgent

from .agent import LANGCHAIN_AVAILABLE

if LANGCHAIN_AVAILABLE:
    from .agent import AgentStreamingSynthesis, AgentSynthesisConfig


class VoiceTurn:
    """
    Orchestrates a complete voice turn.

    Handles:
    - STT transcription
    - LLM + TTS streaming (via StreamingSynthesis or AgentStreamingSynthesis)
    - WebSocket message state machine

    Args:
        stt: Speech-to-text provider
        llm: Language model provider
        tts: Text-to-speech provider
        websocket: WebSocket connection wrapper
        config: Synthesis configuration
        turn_context: Per-turn context for cancellation
        connection_state: Optional shared state machine. If not provided,
            creates an internal one (for isolated testing).
        agent: Optional LangChain agent for non-blocking tool execution

    Usage:
        turn = VoiceTurn(
            stt=stt,
            llm=llm,
            tts=tts,
            websocket=ws,
            config=synthesis_config,
            turn_context=turn_context,
            connection_state=session.connection_state,
        )
        result = await turn.execute(audio_data)

    Usage with Agent:
        turn = VoiceTurn(
            stt=stt,
            llm=llm,
            tts=tts,
            websocket=ws,
            config=synthesis_config,
            turn_context=turn_context,
            agent=booking_agent,
        )
        result = await turn.execute(audio_data)
    """

    def __init__(
        self,
        stt,  # BaseSTT
        llm,  # BaseLLM
        tts,  # BaseTTS
        websocket: WebSocketConnection,
        config: SynthesisConfig,
        turn_context: "TurnContext",
        connection_state: Optional[ConnectionStateMachine] = None,
        agent: Optional["BaseAgent"] = None,
    ):
        self._stt = stt
        self._llm = llm
        self._tts = tts
        self._ws = websocket
        self._config = config
        self._turn_context = turn_context
        self._state = connection_state or ConnectionStateMachine()
        self._agent = agent

    async def execute(self, audio_data: np.ndarray) -> str:
        """
        Execute a complete voice turn.

        Args:
            audio_data: Audio numpy array from STT

        Returns:
            Full response string
        """
        self._state.transition_to(ConnectionState.PROCESSING)
        tts_started = False

        try:
            # STT stage
            transcript, success = await self._stt.transcribe(audio_data)
            self._turn_context.transcript = transcript
            await self._ws.send_transcript(transcript)
            logger.info(f"🎤 Transcript: {transcript}")

            if not transcript.strip() or not success:
                self._state.transition_to(ConnectionState.IDLE)
                await self._ws.send_listening_stopped()
                return ""

            # LLM + TTS streaming
            self._state.transition_to(ConnectionState.SPEAKING)
            await self._ws.send_tts_start()
            tts_started = True

            if self._agent is not None and LANGCHAIN_AVAILABLE:
                synthesis = AgentStreamingSynthesis(
                    agent=self._agent,
                    tts=self._tts,
                    websocket=self._ws,
                    config=AgentSynthesisConfig(
                        sample_rate=self._config.sample_rate,
                        subtitle_streaming=self._config.subtitle_streaming,
                    ),
                    turn_context=self._turn_context,
                )
            else:
                synthesis = StreamingSynthesis(
                    llm=self._llm,
                    tts=self._tts,
                    websocket=self._ws,
                    config=self._config,
                    turn_context=self._turn_context,
                )

            try:
                result = await synthesis.run(transcript)
                full_response = result.full_response
                self._turn_context.full_response = full_response
                self._turn_context.perf_data = {
                    "llm_ttft_ms": result.metrics.llm_ttft_ms,
                    "llm_gen_ms": result.metrics.llm_gen_ms,
                    "tts_ttfa_ms": result.metrics.tts_ttfa_ms,
                    "tts_total_ms": result.metrics.tts_total_ms,
                    "audio_chunks_sent": result.metrics.audio_chunks_sent,
                }

                await self._ws.send_tts_end(interrupted=False)
                await self._ws.send_response_complete(full_response)
                self._state.transition_to(ConnectionState.IDLE)
                await self._ws.send_listening_stopped()

                return full_response

            except asyncio.CancelledError:
                logger.info("🔴 Response task cancelled")
                raise

        except asyncio.CancelledError:
            logger.info("🔴 Voice turn cancelled")
            if tts_started:
                try:
                    fallback = "Sorry, let me start over."
                    await self._ws.send_response_complete(fallback)
                    await self._ws.send_tts_end(interrupted=True)
                except Exception:
                    pass  # WebSocket may already be closed
            raise
        except Exception as e:
            logger.error(f"AI/TTS error: {type(e).__name__}: {e}")
            fallback = "Sorry, I had trouble processing that. Could you try again?"
            try:
                await self._ws.send_response_complete(fallback)
            except Exception:
                pass
            if tts_started:
                try:
                    await self._ws.send_tts_end(interrupted=True)
                except Exception:
                    pass
            raise
