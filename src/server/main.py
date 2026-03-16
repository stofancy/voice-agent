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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger
from pydantic_settings import BaseSettings

# Bailian modules
from .bailian_stt import BailianSTT
from .bailian_tts import BailianTTS
from .backend import AIBackend
from .vad import VoiceActivityDetector
from .auth import token_manager, load_keys_from_env, APIKey
from .text_utils import clean_for_speech


# Streaming configuration from environment
TTS_STREAMING = os.getenv("OPENCLAW_TTS_STREAMING", "true").lower() == "true"
SUBTITLE_STREAMING = os.getenv("OPENCLAW_SUBTITLE_STREAMING", "true").lower() == "true"


class Settings(BaseSettings):
    """Server configuration."""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8765
    
    # Auth
    require_auth: bool = False  # Set True for production
    master_key: Optional[str] = None  # Admin key for full access
    
    # Bailian API
    bailian_api_key: Optional[str] = None  # 百炼 API Key
    
    # STT (Bailian)
    stt_model: str = "qwen3-asr-flash"  # 百炼 STT 模型
    stt_language: str = "zh"  # 识别语言
    
    # TTS (Bailian)
    tts_model: str = "qwen3-tts-flash"  # 百炼 TTS 模型
    tts_voice: str = "Cherry"  # 音色：Cherry, Bella, etc.
    tts_language: str = "Chinese"  # 合成语言
    
    # AI Backend
    backend_type: str = "openclaw"  # openclaw, openai, custom
    backend_url: str = "https://api.openai.com/v1"
    backend_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None
    
    # OpenClaw Gateway (auto-detected from OPENCLAW_GATEWAY_URL + TOKEN)
    openclaw_gateway_url: Optional[str] = None
    openclaw_gateway_token: Optional[str] = None
    
    # Audio
    sample_rate: int = 16000
    
    class Config:
        env_prefix = "OPENCLAW_"
        env_file = ".env"


settings = Settings()
app = FastAPI(title="OpenClaw Voice", version="0.1.0")

# Global instances (initialized on startup)
stt: Optional[BailianSTT] = None
tts: Optional[BailianTTS] = None
backend: Optional[AIBackend] = None
vad: Optional[VoiceActivityDetector] = None


@app.on_event("startup")
async def startup():
    """Initialize models on server start."""
    global stt, tts, backend, vad
    
    logger.info("Initializing OpenClaw Voice server (Bailian Edition)...")
    
    # Load API keys
    load_keys_from_env()
    if settings.require_auth:
        logger.info("🔐 Authentication ENABLED")
    else:
        logger.warning("⚠️ Authentication DISABLED (dev mode)")
    
    # Initialize Bailian STT
    logger.info(f"Loading Bailian STT: {settings.stt_model}")
    stt = BailianSTT(
        api_key=settings.bailian_api_key or os.getenv("ALI_BAILIAN_API_KEY"),
        model=settings.stt_model,
        language=settings.stt_language,
    )
    
    # Initialize Bailian TTS
    logger.info(f"Loading Bailian TTS: {settings.tts_model}")
    tts = BailianTTS(
        api_key=settings.bailian_api_key or os.getenv("ALI_BAILIAN_API_KEY"),
        model=settings.tts_model,
        voice=settings.tts_voice,
        language_type=settings.tts_language,
    )
    
    # Initialize AI backend - Connect to OpenClaw Gateway
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
        # Fallback to Bailian directly
        logger.info("🔌 No Gateway configured - Using Bailian API directly")
        backend = AIBackend(
            backend_type="openai",
            url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-turbo",
            api_key=os.getenv("ALI_BAILIAN_API_KEY"),
        )
    
    # Initialize VAD
    logger.info("Loading VAD model")
    vad = VoiceActivityDetector()
    
    logger.info("✅ OpenClaw Voice server (Bailian) ready!")


@app.get("/")
@app.get("/voice")
@app.get("/voice/")
async def index():
    """Serve the demo page."""
    return FileResponse("src/client/index.html")


@app.post("/api/keys")
async def create_api_key(
    name: str,
    tier: str = "free",
    master_key: Optional[str] = None,
):
    """
    Create a new API key (requires master key).
    
    curl -X POST "http://localhost:8765/api/keys?name=myapp&tier=pro" \
         -H "x-master-key: YOUR_MASTER_KEY"
    """
    # Verify master key
    if settings.require_auth:
        if not master_key and not settings.master_key:
            return {"error": "Master key required"}
        
        provided_key = master_key or ""
        if provided_key != settings.master_key:
            # Also check if it's a valid master-tier key
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
        "api_key": plaintext_key,  # Only shown once!
        "key_id": api_key.key_id,
        "name": api_key.name,
        "tier": api_key.tier,
        "monthly_minutes": api_key.monthly_minutes,
        "rate_limit": api_key.rate_limit_per_minute,
    }


@app.get("/api/usage")
async def get_usage(api_key: str):
    """
    Get usage stats for an API key.
    
    curl "http://localhost:8765/api/usage?api_key=ocv_xxx"
    """
    key = token_manager.validate_key(api_key)
    if not key:
        return {"error": "Invalid API key"}
    
    return token_manager.get_usage(key)


@app.websocket("/ws")
@app.websocket("/voice/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle voice WebSocket connections."""
    # Check for API key in query params or headers
    api_key_str = websocket.query_params.get("api_key") or \
                  websocket.headers.get("x-api-key")
    
    api_key: Optional[APIKey] = None
    
    if settings.require_auth:
        if not api_key_str:
            await websocket.close(code=4001, reason="API key required")
            return
        
        api_key = token_manager.validate_key(api_key_str)
        if not api_key:
            await websocket.close(code=4002, reason="Invalid API key")
            return
        
        if not token_manager.check_rate_limit(api_key):
            await websocket.close(code=4003, reason="Rate limit exceeded")
            return
        
        logger.info(f"Client connected: {api_key.name} (tier={api_key.tier})")
    else:
        # Dev mode - allow all
        if api_key_str:
            api_key = token_manager.validate_key(api_key_str)
        logger.info("Client connected (auth disabled)")
    
    await websocket.accept()
    
    audio_buffer = []
    is_listening = False
    session_start = None
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            # Debug: log all message types
            logger.debug(f"📨 Received: {msg.get('type', 'unknown')}")
            
            if msg["type"] == "start_listening":
                is_listening = True
                audio_buffer = []
                await websocket.send_json({"type": "listening_started"})
                logger.debug("Started listening")
                
            elif msg["type"] == "stop_listening":
                is_listening = False
                
                if audio_buffer:
                    # Combine audio chunks
                    audio_data = np.concatenate(audio_buffer)
                    
                    # Transcribe with Bailian STT
                    logger.debug("Transcribing audio (Bailian STT)...")
                    transcript, success = await stt.transcribe(audio_data)
                    
                    await websocket.send_json({
                        "type": "transcript",
                        "text": transcript,
                        "final": True,
                    })
                    logger.info(f"🎤 Transcript: {transcript}")
                    
                    if transcript.strip() and success:
                        # Get AI response (streaming)
                        logger.debug("Getting AI response (streaming)...")
                        
                        try:
                            # Stream AI response sentence-by-sentence
                            full_response = ""
                            async for chunk in backend.chat_stream(transcript):
                                full_response += chunk
                                # Send subtitle chunk in real-time
                                await websocket.send_json({
                                    "type": "subtitle_chunk",
                                    "text": chunk,
                                })
                                logger.debug(f"📝 Sent subtitle chunk: {chunk[:30]}...")
                            
                            # Synthesize with Bailian TTS (streaming with time + data buffer)
                            logger.debug(f"🔊 Synthesizing response (streaming): {full_response[:50]}...")
                            
                            # Stream TTS audio chunks with buffering
                            tts_start_time = asyncio.get_event_loop().time()
                            audio_chunks_sent = 0
                            buffer = bytearray()
                            first_chunk_received = False
                            buffer_start_time = None
                            
                            async for audio_chunk in tts.synthesize(full_response, stream=True):
                                buffer.extend(audio_chunk)
                                
                                # 记录第一个音频块的到达时间
                                if not first_chunk_received:
                                    first_chunk_received = True
                                    buffer_start_time = asyncio.get_event_loop().time()
                                    logger.info(f"🔊 TTS 收到首块，开始 {TTS_TIME_BUFFER_SECONDS}秒缓冲...")
                                
                                # 当缓冲区足够大且时间缓冲足够时发送
                                current_time = asyncio.get_event_loop().time()
                                time_buffer_elapsed = (current_time - buffer_start_time) if buffer_start_time else 0
                                
                                if len(buffer) >= TTS_DATA_BUFFER_SIZE and time_buffer_elapsed >= TTS_TIME_BUFFER_SECONDS:
                                    audio_b64 = base64.b64encode(bytes(buffer)).decode()
                                    await websocket.send_json({
                                        "type": "audio_chunk",
                                        "data": audio_b64,
                                        "sample_rate": 24000,
                                    })
                                    audio_chunks_sent += 1
                                    chunk_time = asyncio.get_event_loop().time()
                                    logger.debug(f"🔊 发送缓冲音频块 #{audio_chunks_sent}: {len(buffer)} bytes, 总延迟 {(chunk_time - tts_start_time)*1000:.1f}ms (时间缓冲：{time_buffer_elapsed_ms:.1f}ms)")
                                    buffer = bytearray()  # 清空缓冲区
                                    buffer_start_time = asyncio.get_event_loop().time()  # 重置时间缓冲
                            
                            # 发送剩余数据
                            if buffer:
                                audio_b64 = base64.b64encode(bytes(buffer)).decode()
                                await websocket.send_json({
                                    "type": "audio_chunk",
                                    "data": audio_b64,
                                    "sample_rate": 24000,
                                })
                                audio_chunks_sent += 1
                                logger.debug(f"🔊 发送最后音频块 #{audio_chunks_sent}: {len(buffer)} bytes")
                            
                            tts_total_time = asyncio.get_event_loop().time() - tts_start_time
                            logger.info(f"🔊 TTS 完成：{audio_chunks_sent} 块，总耗时 {tts_total_time*1000:.1f}ms")
                            
                            await websocket.send_json({
                                "type": "response_complete",
                                "text": full_response,
                            })
                            logger.info(f"✅ Response complete: {full_response[:100]}...")
                            
                        except Exception as e:
                            logger.error(f"AI/TTS error: {type(e).__name__}: {e}")
                            # Send fallback response
                            fallback = "Sorry, I had trouble processing that. Could you try again?"
                            await websocket.send_json({
                                "type": "response_chunk",
                                "text": fallback,
                            })
                            await websocket.send_json({
                                "type": "response_complete",
                                "text": fallback,
                            })
                
                audio_buffer = []
                await websocket.send_json({"type": "listening_stopped"})
                logger.debug("Stopped listening")
                
            elif msg["type"] == "audio" and is_listening:
                # Decode base64 audio
                audio_bytes = base64.b64decode(msg["data"])
                audio_np = np.frombuffer(audio_bytes, dtype=np.float32)
                audio_buffer.append(audio_np)
                logger.debug(f"📥 Audio chunk: {len(audio_np)} samples, buffer now: {len(audio_buffer)} chunks, total: {sum(len(c) for c in audio_buffer)} samples")
                
                # VAD check - notify client if speech detected
                if vad and len(audio_np) > 0:
                    has_speech = vad.is_speech(audio_np)
                    await websocket.send_json({
                        "type": "vad_status",
                        "speech_detected": has_speech,
                    })
                
            elif msg["type"] == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


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
                            })
                
                audio_buffer = []
                await websocket.send_json({"type": "listening_stopped"})
                logger.debug("Stopped listening")
                
            elif msg["type"] == "audio" and is_listening:
                # Decode base64 audio
                audio_bytes = base64.b64decode(msg["data"])
                audio_np = np.frombuffer(audio_bytes, dtype=np.float32)
                audio_buffer.append(audio_np)
                logger.debug(f"📥 Audio chunk: {len(audio_np)} samples, buffer now: {len(audio_buffer)} chunks, total: {sum(len(c) for c in audio_buffer)} samples")
                
                # VAD check - notify client if speech detected
                if vad and len(audio_np) > 0:
                    has_speech = vad.is_speech(audio_np)
                    await websocket.send_json({
                        "type": "vad_status",
                        "speech_detected": has_speech,
                    })
                
            elif msg["type"] == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


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
ue,
    )
es for client
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
