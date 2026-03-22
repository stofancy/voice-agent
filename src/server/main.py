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
import os
from pathlib import Path
from typing import Optional

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
from .vad import VoiceActivityDetector
from .messages import parse_message
from .websocket_session import WebSocketSession
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

stt = None
tts = None
backend = None
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

    stt = create_stt(
        provider=settings.stt_provider,
        api_key=settings.stt_api_key,
        model=settings.stt_model,
        base_url=settings.stt_base_url,
        language=settings.stt_language,
    )

    tts_instructions = os.getenv("OPENCLAW_TTS_INSTRUCTIONS")
    tts = create_tts(
        provider=settings.tts_provider,
        api_key=settings.tts_api_key,
        model=settings.tts_model,
        voice=settings.tts_voice,
        base_url=settings.tts_base_url,
        language_type=settings.tts_language,
        instructions=tts_instructions,
    )

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

    session = WebSocketSession(websocket)
    last_perf_data: dict = {}
    last_transcript: str = ""
    last_response: str = ""

    try:
        async for raw in _message_stream(websocket):
            message = parse_message(raw)
            msg_type = message.type.value
            logger.debug(f"📨 Received: {msg_type}")

            if msg_type == "start_listening":
                await handle_start_listening(session)

            elif msg_type == "stop_listening":
                task = await handle_stop_listening(
                    session=session,
                    stt=stt,
                    backend=backend,
                    tts=tts,
                    TTS_DATA_BUFFER_SIZE=TTS_DATA_BUFFER_SIZE,
                    TTS_TIME_BUFFER_SECONDS=TTS_TIME_BUFFER_SECONDS,
                    TTS_SAMPLE_RATE=TTS_SAMPLE_RATE,
                    SUBTITLE_STREAMING=SUBTITLE_STREAMING,
                )
                if task is None and session.is_idle:
                    continue

            elif msg_type == "interrupt":
                await handle_interrupt(session)

            elif msg_type == "audio" and session.is_listening:
                await handle_audio(session=session, message=message, vad=vad)

            elif msg_type == "ping":
                await handle_ping(session)

            elif msg_type == "perf_report":
                await handle_perf_report(
                    session=session,
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
        await session.cancel_response(send_interrupt_event=False)
        _close_websocket(websocket)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await session.cancel_response(send_interrupt_event=False)
        _close_websocket(websocket)


async def _message_stream(websocket: WebSocket):
    """Yield incoming text messages from WebSocket."""
    while True:
        yield await websocket.receive_text()


def _close_websocket(websocket: WebSocket) -> None:
    """Close WebSocket, ignoring already-closed errors."""
    try:
        websocket.close()
    except (WebSocketDisconnect, RuntimeError):
        pass  # WebSocket already closed


client_dir = Path(__file__).parent.parent / "client"
if client_dir.exists():
    v2_dir = client_dir / "v2"
    if v2_dir.exists():
        app.mount("/v2", StaticFiles(directory=str(v2_dir), html=True), name="v2-static")
    app.mount("/static", StaticFiles(directory=str(client_dir)), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.server.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
