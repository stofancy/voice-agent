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
from pathlib import Path
from typing import Optional

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic_settings import BaseSettings

# Load .env.local for development (project root)
load_dotenv(Path(__file__).parent.parent.parent / ".env.local")

from .auth import APIKey, load_keys_from_env, token_manager
from .backend import AIBackend
from .bailian_stt import BailianSTT
from .bailian_tts import BailianTTS
from .text_utils import clean_for_speech
from .vad import VoiceActivityDetector


TTS_STREAMING = os.getenv("OPENCLAW_TTS_STREAMING", "true").lower() == "true"
SUBTITLE_STREAMING = os.getenv("OPENCLAW_SUBTITLE_STREAMING", "true").lower() == "true"
TTS_DATA_BUFFER_SIZE = int(os.getenv("OPENCLAW_TTS_DATA_BUFFER_SIZE", "8192"))
TTS_TIME_BUFFER_SECONDS = float(os.getenv("OPENCLAW_TTS_TIME_BUFFER_SECONDS", "0.1"))
TTS_SAMPLE_RATE = int(os.getenv("OPENCLAW_TTS_SAMPLE_RATE", "24000"))


class Settings(BaseSettings):
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8765

    require_auth: bool = False
    master_key: Optional[str] = None

    bailian_api_key: Optional[str] = None

    stt_model: str = "qwen3-asr-flash"
    stt_language: str = "zh"

    tts_model: str = "qwen3-tts-flash"
    tts_voice: str = "Cherry"
    tts_language: str = "Chinese"

    sample_rate: int = 16000

    class Config:
        env_prefix = "OPENCLAW_"
        env_file = ".env.local"
        extra = "ignore"


settings = Settings()
app = FastAPI(title="OpenClaw Voice", version="0.1.0")

stt: Optional[BailianSTT] = None
tts: Optional[BailianTTS] = None
backend: Optional[AIBackend] = None
vad: Optional[VoiceActivityDetector] = None


@app.on_event("startup")
async def startup():
    """Initialize models on server start."""
    global stt, tts, backend, vad

    logger.info("Initializing OpenClaw Voice server (Bailian Edition)...")

    load_keys_from_env()
    if settings.require_auth:
        logger.info("🔐 Authentication ENABLED")
    else:
        logger.warning("⚠️ Authentication DISABLED (dev mode)")

    logger.info(f"Loading Bailian STT: {settings.stt_model}")
    stt = BailianSTT(
        api_key=settings.bailian_api_key or os.getenv("ALI_BAILIAN_API_KEY"),
        model=settings.stt_model,
        language=settings.stt_language,
    )

    logger.info(f"Loading Bailian TTS: {settings.tts_model}")
    tts = BailianTTS(
        api_key=settings.bailian_api_key or os.getenv("ALI_BAILIAN_API_KEY"),
        model=settings.tts_model,
        voice=settings.tts_voice,
        language_type=settings.tts_language,
    )

    gateway_url = os.getenv("OPENCLAW_GATEWAY_URL")
    gateway_token = os.getenv("OPENCLAW_GATEWAY_TOKEN")

    if gateway_url and gateway_token:
        logger.info(f"🦞 Connecting to OpenClaw Gateway: {gateway_url}")
        backend = AIBackend(
            backend_type="openai",
            url=f"{gateway_url}/v1",
            model="openclaw:main",
            api_key=gateway_token,
            system_prompt=(
                "This conversation is happening via real-time voice chat. "
                "Keep responses concise and conversational — a few sentences "
                "at most unless the topic genuinely needs depth. "
                "No markdown, bullet points, code blocks, or special formatting."
            ),
        )
    else:
        logger.info("🔌 No Gateway configured - Using Bailian API directly")
        fallback_api_key = os.getenv("ALI_BAILIAN_API_KEY") or os.getenv("OPENAI_API_KEY") or "mock-key"
        if fallback_api_key == "mock-key":
            logger.warning("⚠️ No AI backend key found, using mock key for local/dev startup")
        backend = AIBackend(
            backend_type="openai",
            url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-turbo",
            api_key=fallback_api_key,
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


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "service": "openclaw-voice-backend",
        "version": "0.1.0",
        "components": {
            "stt": "ready" if stt else "not_ready",
            "tts": "ready" if tts else "not_ready",
            "backend": "ready" if backend else "not_ready",
        }
    }


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
@app.websocket("/v2/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle voice WebSocket connections for v1 and v2."""
    api_key = await _validate_ws_auth(websocket)
    if settings.require_auth and not api_key:
        return

    await websocket.accept()

    connection_state = "IDLE"
    audio_buffer: list[np.ndarray] = []
    response_task: Optional[asyncio.Task] = None

    async def send_listening_stopped_once():
        nonlocal connection_state
        await websocket.send_json({"type": "listening_stopped"})
        connection_state = "IDLE"

    async def run_turn(audio_data: np.ndarray):
        nonlocal connection_state
        tts_started = False

        try:
            connection_state = "PROCESSING"
            transcript, success = await stt.transcribe(audio_data)

            try:
                await websocket.send_json(
                    {
                        "type": "transcript",
                        "text": transcript,
                        "final": True,
                    }
                )
                logger.info(f"✅ Transcript sent successfully: {transcript}")
            except Exception as e:
                logger.error(f"❌ Failed to send transcript: {e}")
                raise

            if not transcript.strip() or not success:
                logger.info("🛑 Empty transcript, stopping")
                await send_listening_stopped_once()
                return

            logger.info("🤖 Starting LLM chat stream...")
            full_response = ""
            async for chunk in backend.chat_stream(transcript):
                full_response += chunk
                if SUBTITLE_STREAMING:
                    await websocket.send_json({"type": "subtitle_chunk", "text": chunk})

            if not SUBTITLE_STREAMING:
                await websocket.send_json({"type": "response_chunk", "text": full_response})

            speech_text = clean_for_speech(full_response)
            tts_started = True
            connection_state = "SPEAKING"
            await websocket.send_json({"type": "tts_start"})

            tts_start_time = asyncio.get_event_loop().time()
            audio_chunks_sent = 0
            buffer = bytearray()
            first_chunk_received = False
            buffer_start_time: Optional[float] = None

            async for audio_chunk in tts.synthesize(speech_text, stream=TTS_STREAMING):
                buffer.extend(audio_chunk)

                if not first_chunk_received:
                    first_chunk_received = True
                    buffer_start_time = asyncio.get_event_loop().time()
                    logger.info(f"🔊 TTS first chunk, buffering {TTS_TIME_BUFFER_SECONDS}s...")

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
                        {
                            "type": "audio_chunk",
                            "data": audio_b64,
                            "sample_rate": TTS_SAMPLE_RATE,
                        }
                    )
                    audio_chunks_sent += 1
                    chunk_time = asyncio.get_event_loop().time()
                    logger.debug(
                        "🔊 sent chunk #{}: {} bytes, latency {:.1f}ms (buffer {:.1f}ms)",
                        audio_chunks_sent,
                        len(buffer),
                        (chunk_time - tts_start_time) * 1000,
                        time_buffer_elapsed * 1000,
                    )
                    buffer = bytearray()
                    buffer_start_time = asyncio.get_event_loop().time()

            if buffer:
                audio_b64 = base64.b64encode(bytes(buffer)).decode()
                await websocket.send_json(
                    {
                        "type": "audio_chunk",
                        "data": audio_b64,
                        "sample_rate": TTS_SAMPLE_RATE,
                    }
                )
                audio_chunks_sent += 1

            tts_total_time = asyncio.get_event_loop().time() - tts_start_time
            logger.info(
                "🔊 TTS complete: {} chunks, total {:.1f}ms",
                audio_chunks_sent,
                tts_total_time * 1000,
            )

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
                # 如果正在处理 STT，不取消任务，返回错误
                if connection_state == "PROCESSING":
                    logger.warning("⚠️ STT 处理中，忽略 start_listening")
                    await websocket.send_json({
                        "type": "error",
                        "message": "正在处理上一个请求，请稍候"
                    })
                    continue
                
                await cancel_response(send_interrupt_event=False)
                audio_buffer = []
                connection_state = "LISTENING"
                await websocket.send_json({"type": "listening_started"})

            elif msg_type == "stop_listening":
                logger.info(f"🛑 stop_listening: state={connection_state}, buffer_size={len(audio_buffer)}")
                if connection_state != "LISTENING":
                    logger.warning(f"⚠️ stop_listening but state={connection_state}")
                    await send_listening_stopped_once()
                    continue

                connection_state = "PROCESSING"
                if not audio_buffer:
                    logger.warning("⚠️ stop_listening but audio_buffer is empty")
                    await send_listening_stopped_once()
                    continue

                audio_data = np.concatenate(audio_buffer)
                audio_buffer = []
                logger.info(f"🎵 Starting STT: {len(audio_data)} samples, {len(audio_data)/16000:.2f}s")
                response_task = asyncio.create_task(run_turn(audio_data))

            elif msg_type == "interrupt":
                await websocket.send_json({"type": "interrupt_ack"})
                await cancel_response(send_interrupt_event=True)

            elif msg_type == "audio":
                logger.debug(f"🎵 Audio received, state={connection_state}, size={len(msg.get('data', ''))}")
                if connection_state != "LISTENING":
                    logger.warning(f"⚠️ Audio received but state={connection_state}, expected LISTENING")
                    continue
                    
                audio_bytes = base64.b64decode(msg["data"])
                audio_np = np.frombuffer(audio_bytes, dtype=np.float32)
                audio_buffer.append(audio_np)
                logger.debug(f"📦 Audio buffered, total chunks={len(audio_buffer)}")

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

    except WebSocketDisconnect:
        logger.info("Client disconnected")
        await cancel_response(send_interrupt_event=False)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await cancel_response(send_interrupt_event=False)
        await websocket.close()


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
