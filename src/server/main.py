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
from .audio import AudioBuffer
from .streaming_synthesis import StreamingSynthesis, SynthesisConfig
from .connection import WebSocketConnection, ConnectionStateMachine, ConnectionState
from .turn_context import TurnContext
from .voice_turn import VoiceTurn
from .messages import parse_message, MessageType
from .message_router import (
    handle_start_listening,
    handle_stop_listening,
    handle_interrupt,
    handle_audio,
    handle_ping,
    handle_perf_report,
)


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

    connection_state = ConnectionStateMachine()
    audio_buffer = AudioBuffer()
    response_task: Optional[asyncio.Task] = None
    turn_context = TurnContext()

    last_perf_data: dict = {}
    last_transcript: str = ""
    last_response: str = ""

    async def send_listening_stopped_once():
        nonlocal connection_state
        await websocket.send_json({"type": "listening_stopped"})
        connection_state.transition_to(ConnectionState.IDLE)

    async def cancel_response(send_interrupt_event: bool):
        nonlocal response_task
        turn_context.cancel()
        if response_task and not response_task.done():
            response_task.cancel()
            try:
                await response_task
            except asyncio.CancelledError:
                pass
        response_task = None
        if send_interrupt_event:
            await websocket.send_json({"type": "interrupt_complete"})

    try:
        while True:
            raw = await websocket.receive_text()
            message = parse_message(raw)
            msg_type = message.type.value
            logger.debug(f"📨 Received: {msg_type}")

            if msg_type == "start_listening":
                await handle_start_listening(
                    websocket=websocket,
                    connection_state=connection_state,
                    audio_buffer=audio_buffer,
                    cancel_callback=cancel_response,
                )

            elif msg_type == "stop_listening":
                new_task = await handle_stop_listening(
                    websocket=websocket,
                    connection_state=connection_state,
                    audio_buffer=audio_buffer,
                    turn_context=turn_context,
                    send_listening_stopped_once=send_listening_stopped_once,
                    stt=stt,
                    backend=backend,
                    tts=tts,
                    TTS_DATA_BUFFER_SIZE=TTS_DATA_BUFFER_SIZE,
                    TTS_TIME_BUFFER_SECONDS=TTS_TIME_BUFFER_SECONDS,
                    TTS_SAMPLE_RATE=TTS_SAMPLE_RATE,
                    SUBTITLE_STREAMING=SUBTITLE_STREAMING,
                )
                if new_task is None and connection_state.is_idle():
                    # Early continue was triggered in handler
                    continue
                if new_task:
                    response_task = new_task

            elif msg_type == "interrupt":
                await handle_interrupt(
                    websocket=websocket,
                    cancel_callback=cancel_response,
                )

            elif msg_type == "audio" and connection_state.is_listening():
                await handle_audio(
                    message=message,
                    websocket=websocket,
                    connection_state=connection_state,
                    audio_buffer=audio_buffer,
                    vad=vad,
                )

            elif msg_type == "ping":
                await handle_ping(websocket=websocket)

            elif msg_type == "perf_report":
                await handle_perf_report(
                    message=message,
                    perf_logger=perf_logger,
                    last_transcript=last_transcript,
                    last_response=last_response,
                    last_perf_data=last_perf_data,
                    settings=settings,
                    backend=backend,
                )

    except WebSocketDisconnect:
        logger.info("Client disconnected")
        await cancel_response(send_interrupt_event=False)
        try:
            await websocket.close()
        except (WebSocketDisconnect, RuntimeError):
            pass  # WebSocket already closed
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await cancel_response(send_interrupt_event=False)
        try:
            await websocket.close()
        except (WebSocketDisconnect, RuntimeError):
            pass  # WebSocket already closed


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
