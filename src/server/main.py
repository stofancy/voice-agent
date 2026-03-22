"""
OpenClaw Voice Server - Bailian Edition

WebSocket server that handles:
- Audio input from browser
- Speech-to-Text via Alibaba Bailian (Qwen-ASR)
- AI backend communication (OpenClaw Gateway)
- Text-to-Speech via Alibaba Bailian (Qwen-TTS)
- Audio streaming back to browser
"""

import asyncio
import base64
import json
import os
import time
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic_settings import BaseSettings

from . import perf_logger
from .auth import APIKey, load_keys_from_env, token_manager
from .tts import create_tts
from .stt import create_stt
from .llm import create_llm
from .text_utils import clean_for_speech
from .vad import VoiceActivityDetector


TTS_STREAMING = os.getenv("OPENCLAW_TTS_STREAMING", "true").lower() == "true"
SUBTITLE_STREAMING = os.getenv("OPENCLAW_SUBTITLE_STREAMING", "true").lower() == "true"
TTS_DATA_BUFFER_SIZE = int(os.getenv("OPENCLAW_TTS_DATA_BUFFER_SIZE", "8192"))
TTS_TIME_BUFFER_SECONDS = float(os.getenv("OPENCLAW_TTS_TIME_BUFFER_SECONDS", "0.1"))
TTS_SAMPLE_RATE = int(os.getenv("OPENCLAW_TTS_SAMPLE_RATE", "24000"))


# Streaming configuration from environment
TTS_STREAMING = os.getenv("OPENCLAW_TTS_STREAMING", "true").lower() == "true"
SUBTITLE_STREAMING = os.getenv("OPENCLAW_SUBTITLE_STREAMING", "true").lower() == "true"


class Settings(BaseSettings):
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8765

    require_auth: bool = False
    master_key: Optional[str] = None

    stt_provider: str
    stt_api_key: str
    stt_model: Optional[str] = None
    stt_base_url: Optional[str] = None
    stt_language: str = "zh"

    tts_provider: str
    tts_api_key: str
    tts_model: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_base_url: Optional[str] = None
    tts_language: str = "Chinese"

    llm_provider: str
    llm_api_key: str
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None

    class Config:
        env_prefix = "OPENCLAW_"
        env_file = ".env"
        extra = "allow"


settings = Settings()
app = FastAPI(title="OpenClaw Voice", version="0.1.0")

stt = None  # BaseSTT instance, created by stt_factory
tts = None  # BaseTTS instance, created by tts_factory
backend = None  # BaseLLM instance, created by llm_factory
vad: Optional[VoiceActivityDetector] = None


@app.on_event("startup")
async def startup():
    """Initialize models on server start."""
    global stt, tts, backend, vad

    logger.info("Initializing OpenClaw Voice server (Bailian Edition)...")
    logger.info(f"TTS config: DATA_BUFFER={TTS_DATA_BUFFER_SIZE} bytes, TIME_BUFFER={TTS_TIME_BUFFER_SECONDS}s, STREAMING={TTS_STREAMING}")

    load_keys_from_env()
    if settings.require_auth:
        logger.info("🔐 Authentication ENABLED")
    else:
        logger.warning("⚠️ Authentication DISABLED (dev mode)")

    logger.info(f"Loading STT: provider={settings.stt_provider}, model={settings.stt_model}")
    stt = create_stt(
        provider=settings.stt_provider,
        api_key=settings.stt_api_key,
        model=settings.stt_model,
        base_url=settings.stt_base_url,
        language=settings.stt_language,
    )

    tts_instructions = os.getenv("OPENCLAW_TTS_INSTRUCTIONS")
    logger.info(f"Loading TTS: provider={settings.tts_provider}, model={settings.tts_model}")
    tts = create_tts(
        provider=settings.tts_provider,
        api_key=settings.tts_api_key,
        model=settings.tts_model,
        voice=settings.tts_voice,
        base_url=settings.tts_base_url,
        language_type=settings.tts_language,
        instructions=tts_instructions,
    )

    logger.info(f"Loading LLM: provider={settings.llm_provider}, model={settings.llm_model}")
    backend = create_llm(
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        system_prompt=(
            "This conversation is happening via real-time voice chat. "
            "Keep responses concise and conversational — a few sentences "
            "at most unless the topic genuinely needs depth. "
            "No markdown, bullet points, code blocks, or special formatting."
        ),
    )

    logger.info("Loading VAD model")
    vad = VoiceActivityDetector()

    logger.info("✅ OpenClaw Voice server (Bailian) ready!")


@app.on_event("shutdown")
async def shutdown():
    """Release network resources on server stop."""
    global backend
    if backend:
        await backend.close()
        logger.info("✅ Backend connections closed")


@app.get("/")
@app.get("/voice")
@app.get("/voice/")
async def index():
    """Serve v1 demo page."""
    return FileResponse("src/client/index.html")


@app.post("/api/keys")
async def create_api_key(
    name: str,
    tier: str = "free",
    master_key: Optional[str] = None,
):
    """Create a new API key (requires master key)."""
    if settings.require_auth:
        if not master_key and not settings.master_key:
            return {"error": "Master key required"}

        provided_key = master_key or ""
        if provided_key != settings.master_key:
            key = token_manager.validate_key(provided_key)
            if not key or key.tier != "enterprise":
                return {"error": "Invalid master key"}

    from .auth import PRICING_TIERS

    if tier not in PRICING_TIERS:
        return {"error": f"Invalid tier. Options: {list(PRICING_TIERS.keys())}"}

    tier_config = PRICING_TIERS[tier]
    plaintext_key, api_key = token_manager.generate_key(
        name=name,
        tier=tier,
        rate_limit=tier_config["rate_limit"],
        monthly_minutes=tier_config["monthly_minutes"],
    )

    return {
        "api_key": plaintext_key,
        "key_id": api_key.key_id,
        "name": api_key.name,
        "tier": api_key.tier,
        "monthly_minutes": api_key.monthly_minutes,
        "rate_limit": api_key.rate_limit_per_minute,
    }


@app.get("/api/usage")
async def get_usage(api_key: str):
    """Get usage stats for an API key."""
    key = token_manager.validate_key(api_key)
    if not key:
        return {"error": "Invalid API key"}

    return token_manager.get_usage(key)


async def _validate_ws_auth(websocket: WebSocket) -> Optional[APIKey]:
    """Validate websocket auth and close with proper code on failure."""
    api_key_str = websocket.query_params.get("api_key") or websocket.headers.get("x-api-key")
    api_key: Optional[APIKey] = None

    if settings.require_auth:
        if not api_key_str:
            await websocket.close(code=4001, reason="API key required")
            return None

        api_key = token_manager.validate_key(api_key_str)
        if not api_key:
            await websocket.close(code=4002, reason="Invalid API key")
            return None

        if not token_manager.check_rate_limit(api_key):
            await websocket.close(code=4003, reason="Rate limit exceeded")
            return None

        logger.info(f"Client connected: {api_key.name} (tier={api_key.tier})")
    else:
        if api_key_str:
            api_key = token_manager.validate_key(api_key_str)
        logger.info("Client connected (auth disabled)")

    return api_key


@app.websocket("/ws")
@app.websocket("/voice/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle voice WebSocket connections for v1 and v2."""
    api_key = await _validate_ws_auth(websocket)
    if settings.require_auth and not api_key:
        return

    await websocket.accept()

    connection_state = "IDLE"
    audio_buffer: list[np.ndarray] = []
    response_task: Optional[asyncio.Task] = None

    last_perf_data: dict = {}
    last_transcript: str = ""
    last_response: str = ""

    async def send_listening_stopped_once():
        nonlocal connection_state
        await websocket.send_json({"type": "listening_stopped"})
        connection_state = "IDLE"

    async def run_turn(audio_data: np.ndarray):
        nonlocal connection_state, last_transcript, last_response, last_perf_data
        tts_started = False

        # Perf data dict, only populated when perf logging is enabled
        perf_data: dict = {}
        t_llm_first: Optional[float] = None
        t_llm_end: Optional[float] = None
        t_tts_first: Optional[float] = None
        t_tts_end: Optional[float] = None

        try:
            connection_state = "PROCESSING"

            # ── STT stage ──────────────────────────────────────────
            if perf_logger.is_enabled():
                t_start = time.perf_counter()

            transcript, success = await stt.transcribe(audio_data)

            if perf_logger.is_enabled():
                t_stt_end = time.perf_counter()
                perf_data["stt_ms"] = (t_stt_end - t_start) * 1000

            last_transcript = transcript
            await websocket.send_json(
                {
                    "type": "transcript",
                    "text": transcript,
                    "final": True,
                }
            )
            logger.info(f"🎤 Transcript: {transcript}")

            if not transcript.strip() or not success:
                await send_listening_stopped_once()
                if perf_logger.is_enabled():
                    last_perf_data = perf_data
                return

            # ── LLM + TTS stage (parallel execution) ─────────
            full_response = ""
            tts_stream = tts.create_stream()
            tts_started = True
            connection_state = "SPEAKING"
            await websocket.send_json({"type": "tts_start"})

            async def llm_feed_loop():
                """LLM 产生 token → feed 给 TTS → 发送字幕"""
                nonlocal full_response, t_llm_first
                t_llm_first = None  # 避免 UnboundLocalError
                try:
                    async for chunk in backend.chat_stream(transcript):
                        full_response += chunk
                        if perf_logger.is_enabled() and t_llm_first is None:
                            t_llm_first = time.perf_counter()
                            perf_data["llm_ttft_ms"] = (t_llm_first - t_stt_end) * 1000
                        if SUBTITLE_STREAMING:
                            await websocket.send_json({"type": "subtitle_chunk", "text": chunk})
                        tts_stream.feed(chunk)
                finally:
                    tts_stream.finish()  # 保证 finish() 被调用
                    t_llm_end = time.perf_counter()
                if perf_logger.is_enabled() and t_llm_first is not None:
                    perf_data["llm_gen_ms"] = (t_llm_end - t_llm_first) * 1000

            async def tts_consume_loop():
                """TTS 音频边产生边发送"""
                nonlocal audio_chunks_sent, t_tts_first, t_llm_end
                logger.info("🔊 TTS consume loop started")
                # 确保 TTS stream 已初始化（feed 会触发懒连接）
                tts_stream._ensure_connected()
                logger.info("🔊 TTS stream ensured connected")
                buffer = bytearray()
                first_chunk_received = False
                buffer_start_time: Optional[float] = None
                tts_start_time = asyncio.get_event_loop().time()
                try:
                    async for audio_chunk in tts_stream:
                        buffer.extend(audio_chunk)

                        if not first_chunk_received:
                            first_chunk_received = True
                            t_tts_first = time.perf_counter()
                            if perf_logger.is_enabled():
                                perf_data["tts_ttfa_ms"] = (t_tts_first - t_llm_end) * 1000
                            buffer_start_time = asyncio.get_event_loop().time()
                            logger.info(f"🔊 TTS first chunk received, buffering {TTS_TIME_BUFFER_SECONDS}s...")

                        current_time = asyncio.get_event_loop().time()
                        time_buffer_elapsed = (
                            (current_time - buffer_start_time) if buffer_start_time is not None else 0
                        )

                        if (
                            len(buffer) >= TTS_DATA_BUFFER_SIZE
                            and time_buffer_elapsed >= TTS_TIME_BUFFER_SECONDS
                        ):
                            audio_b64 = base64.b64encode(bytes(buffer)).decode()
                            await websocket.send_json(
                                {"type": "audio_chunk", "data": audio_b64, "sample_rate": TTS_SAMPLE_RATE}
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
                        audio_b64 = base64.b64encode(bytes(buffer)).decode()
                        await websocket.send_json(
                            {"type": "audio_chunk", "data": audio_b64, "sample_rate": TTS_SAMPLE_RATE}
                        )
                        audio_chunks_sent += 1
                    logger.info(f"🔊 TTS consume loop finished, sent {audio_chunks_sent} chunks")
                except asyncio.CancelledError:
                    logger.warning("🔊 TTS consume loop cancelled")
                    raise  # 重新抛出以符合 asyncio.gather 取消语义
                except Exception as e:
                    logger.error(f"🔊 TTS consume loop error: {e}")
                    raise

            # 并行执行 LLM feed 和 TTS consume
            tts_start_time = asyncio.get_event_loop().time()
            audio_chunks_sent = 0
            await asyncio.gather(llm_feed_loop(), tts_consume_loop())

            tts_total_time = asyncio.get_event_loop().time() - tts_start_time
            logger.info("🔊 TTS complete: {} chunks, total {:.1f}ms", audio_chunks_sent, tts_total_time * 1000)

            if perf_logger.is_enabled():
                last_perf_data = perf_data

            await websocket.send_json({"type": "tts_end", "interrupted": False})
            await websocket.send_json({"type": "response_complete", "text": full_response})
            await send_listening_stopped_once()

        except asyncio.CancelledError:
            logger.info("🔴 Response task cancelled")
            if tts_started:
                await websocket.send_json({"type": "tts_end", "interrupted": True})
            await send_listening_stopped_once()
            raise
        except Exception as e:
            logger.error(f"AI/TTS error: {type(e).__name__}: {e}")
            fallback = "Sorry, I had trouble processing that. Could you try again?"
            await websocket.send_json({"type": "response_chunk", "text": fallback})
            await websocket.send_json({"type": "response_complete", "text": fallback})
            if tts_started:
                await websocket.send_json({"type": "tts_end", "interrupted": True})
            await send_listening_stopped_once()

    async def cancel_response(send_interrupt_event: bool):
        nonlocal response_task
        if response_task and not response_task.done():
            response_task.cancel()
            try:
                await response_task
            except asyncio.CancelledError:
                pass
            if send_interrupt_event:
                await websocket.send_json({"type": "interrupt_complete"})
        response_task = None

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type")
            logger.debug(f"📨 Received: {msg_type}")

            if msg_type == "start_listening":
                await cancel_response(send_interrupt_event=False)
                audio_buffer = []
                connection_state = "LISTENING"
                await websocket.send_json({"type": "listening_started"})

            elif msg_type == "stop_listening":
                if connection_state != "LISTENING":
                    await send_listening_stopped_once()
                    continue

                connection_state = "PROCESSING"
                if not audio_buffer:
                    await send_listening_stopped_once()
                    continue

                audio_data = np.concatenate(audio_buffer)
                audio_buffer = []
                response_task = asyncio.create_task(run_turn(audio_data))

            elif msg_type == "interrupt":
                await websocket.send_json({"type": "interrupt_ack"})
                await cancel_response(send_interrupt_event=True)

            elif msg_type == "audio" and connection_state == "LISTENING":
                audio_bytes = base64.b64decode(msg["data"])
                audio_np = np.frombuffer(audio_bytes, dtype=np.float32)
                audio_buffer.append(audio_np)

                if vad and len(audio_np) > 0:
                    has_speech = vad.is_speech(audio_np)
                    await websocket.send_json(
                        {
                            "type": "vad_status",
                            "speech_detected": has_speech,
                        }
                    )

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "perf_report":
                if perf_logger.is_enabled():
                    frontend_metrics = msg.get("metrics", {})
                    context = {
                        "transcript": last_transcript,
                        "response_length": len(last_response),
                        "tts_model": settings.tts_model,
                        "llm_model": backend.model_name if backend else "unknown",
                        "tts_voice": settings.tts_voice,
                    }
                    perf_logger.log_round(
                        frontend_data=frontend_metrics,
                        backend_data=last_perf_data,
                        context=context,
                    )

    except WebSocketDisconnect:
        logger.info("Client disconnected")
        await cancel_response(send_interrupt_event=False)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await cancel_response(send_interrupt_event=False)
        await websocket.close()


client_dir = Path(__file__).parent.parent / "client"
if client_dir.exists():
    v2_dir = client_dir / "v2"
    if v2_dir.exists():
        app.mount("/v2", StaticFiles(directory=str(v2_dir), html=True), name="v2-static")

# Serve static files for client
client_dir = Path(__file__).parent.parent / "client"
if client_dir.exists():
    app.mount("/static", StaticFiles(directory=str(client_dir)), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.server.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
