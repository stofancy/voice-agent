# OpenClaw Voice - AI Copilot Instructions

**Project**: Self-hosted browser-based voice interface for AI assistants  
**Tech Stack**: FastAPI + WebSockets (Python 3.10+) + Browser UI  
**Last Updated**: March 2026

---

## 🧭 Skill Routing Rules

When a user question is primarily about **OpenClaw** (concepts, architecture, gateway, protocol, memory, tools, skills, plugins, providers, channels, deployment, troubleshooting), the assistant should:

1. **Use `openclaw-docs` skill first** to retrieve authoritative docs context.
2. Prefer documentation-grounded guidance over assumptions.
3. Fall back to repository-only context **only if** docs fetch fails or user explicitly asks for repo-only behavior.

Trigger phrases include (non-exhaustive):
- "OpenClaw", "gateway", "agent", "memory", "tools", "skills", "plugin", "provider", "channel", "protocol", "troubleshooting"
- "how does OpenClaw ...", "integrate with OpenClaw ...", "OpenClaw best practice"

---

## 🏗️ Architecture Overview

### Real-Time Voice Pipeline

```
                    ┌─────────────────────────────────────────┐
                    │        Browser UI Client                 │
                    │  (WebSocket connection, audio capture)   │
                    └──────────────┬──────────────────────────┘
                                   │ Audio (WebSocket)
                    ┌──────────────▼──────────────────────────┐
                    │      FastAPI WebSocket Server            │
                    │      (src/server/main.py)               │
                    └──────────────┬──────────────────────────┘
                                   │ Raw audio stream
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
    ┌────────┐            ┌─────────────┐         ┌──────────────┐
    │ VAD    │            │ Bailian STT │         │ (Optional)   │
    │(Silero)│            │(Qwen-ASR)   │         │ Faster-Whisper│
    │Filter  │            │WebSocket    │         └──────────────┘
    │silence │            │→ Text       │
    └────────┘            └─────────────┘
        │                       │
        └───────────┬───────────┘
                    │ Transcribed text
        ┌───────────▼──────────────────┐
        │   AI Backend                 │
        │  (OpenClaw Gateway / OpenAI) │
        │   chat_stream() generator    │
        └───────────┬──────────────────┘
                    │ Streaming AI response
        ┌───────────▼──────────────────┐
        │  Sentence Streaming & TTS    │
        │  - Accumulate sentences      │
        │  - Send to Bailian TTS       │
        │  - Stream audio back         │
        └───────────┬──────────────────┘
                    │ Audio chunks
                    ▼
            Browser (playback)
```

### Component Responsibilities

| Component | Module | Purpose |
|-----------|--------|---------|
| **Speech-to-Text** | `src/server/bailian_stt.py` | Convert audio → text via Alibaba Qwen-ASR |
| **AI Backend** | `src/server/backend.py` | Connect to OpenAI/OpenClaw/custom (async streaming) |
| **Text-to-Speech** | `src/server/bailian_tts.py` | Stream text → audio via Alibaba Qwen-TTS |
| **Voice Activity Detection** | `src/server/vad.py` | Filter silence using Silero VAD |
| **WebSocket Handler** | `src/server/main.py` | Orchestrate real-time pipeline |
| **Auth** | `src/server/auth.py` | Token management (Telegram Bot API style) |
| **Text Cleaning** | `src/server/text_utils.py` | Strip markdown/URLs/hashtags before TTS |

---

## 📋 Quick Reference

### Environment Variables (`OPENCLAW_` prefix)

**Core Server**:
```env
OPENCLAW_PORT=8765                              # Server port
OPENCLAW_REQUIRE_AUTH=false                     # Require API keys
OPENCLAW_MASTER_KEY=your-admin-key              # Admin access
```

**STT (Speech-to-Text)**:
```env
OPENCLAW_STT_MODEL=qwen3-asr-flash              # Bailian model (or 'whisper')
OPENCLAW_STT_DEVICE=auto                        # CPU/CUDA/MPS auto-detection
OPENCLAW_STT_LANGUAGE=zh                        # Recognition language
```

**TTS (Text-to-Speech)**:
```env
OPENCLAW_TTS_STREAMING=true                     # Enable streaming
OPENCLAW_SUBTITLE_STREAMING=true                # Stream subtitles (WIP)
```

**AI Backend**:
```env
OPENCLAW_BACKEND_TYPE=openclaw                  # openclaw | openai | bailian
OPENCLAW_BACKEND_MODEL=gpt-4o-mini              # Model name
OPENCLAW_GATEWAY_URL=https://...                # OpenClaw Gateway URL
OPENCLAW_GATEWAY_TOKEN=token                    # Gateway auth token
OPENAI_API_KEY=sk-...                           # OpenAI fallback
ALI_BAILIAN_API_KEY=your-bailian-key            # Alibaba Qwen access
```

### Critical Files

**Backend Server**:
- [src/server/main.py](../src/server/main.py) - FastAPI WebSocket server, Settings
- [src/server/backend.py](../src/server/backend.py) - AI backend (OpenAI/OpenClaw/Bailian)
- [src/server/bailian_stt.py](../src/server/bailian_stt.py) - STT implementation
- [src/server/bailian_tts.py](../src/server/bailian_tts.py) - TTS with streaming
- [src/server/auth.py](../src/server/auth.py) - Token-based auth
- [src/server/vad.py](../src/server/vad.py) - Voice activity detection

**Frontend Client**:
- [src/client/index.html](../src/client/index.html) - Main demo page

**Configuration**:
- [pyproject.toml](../pyproject.toml) - Dependencies and project metadata
- [requirements.txt](../requirements.txt) - Pinned versions

### Commands

| Task | Command |
|------|---------|
| **Run locally** | `PYTHONPATH=. python -m src.server.main` |
| **Create .env** | `cp .env.example .env` (then edit) |
| **Build Docker** | `docker compose build openclaw-voice` |
| **Run Docker** | `docker compose up -d` |
| **View logs** | `docker compose logs -f openclaw-voice` |
| **Stop** | `docker compose down` |
| **Tests** | `pytest tests/ -v` |
| **Format** | `black src/ tests/` |
| **Lint** | `ruff check src/ tests/` |

---

## 🔧 Development Workflow

### Setup

```bash
# 1. Clone and navigate
git clone https://github.com/Purple-Horizons/openclaw-voice.git
cd openclaw-voice

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  (Windows)

# 3. Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"  # Install extras for development

# 4. (Optional) Install STT/TTS extras for local models
pip install torch torchaudio  # For VAD, faster-whisper

# 5. Configure
cp .env.example .env
# Edit .env with your API keys (OPENAI_API_KEY, ALI_BAILIAN_API_KEY, etc.)

# 6. Run
PYTHONPATH=. python -m src.server.main
# Server starts at http://localhost:8765
```

### Making Code Changes

**Python (Backend)**:
1. Edit files in `src/server/`
2. Changes auto-reload with `uvicorn` (when `--reload` is used)
3. Run tests: `pytest tests/ -v`

**JavaScript (Frontend)**:
1. Edit [src/client/index.html](../src/client/index.html)
2. browser will auto-reload
3. Check browser DevTools for console errors

**Adding Features**:
- New STT backend? Extend [src/server/bailian_stt.py](../src/server/bailian_stt.py)
- New AI backend? Add to [src/server/backend.py](../src/server/backend.py)
- New auth strategy? Update [src/server/auth.py](../src/server/auth.py)

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_server.py::test_websocket -v

# Run async tests
pytest -asyncio

# Run with coverage
pytest --cov=src tests/
```

---

## 🎯 Key Patterns & Conventions

### Async/Await (FastAPI + WebSockets)

```python
# Stream responses (async generator)
async def chat_stream(message: str) -> AsyncGenerator[str, None]:
    async for chunk in client.chat.completions.create(stream=True):
        yield chunk.choices[0].delta.content

# WebSocket handler
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    async for message in websocket.iter_text():
        # Process message
        await websocket.send_text(response)
```

### Configuration (Pydantic BaseSettings)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    port: int = 8765
    class Config:
        env_prefix = "OPENCLAW_"
        env_file = ".env"

settings = Settings()  # Auto-loads from env vars + .env
```

### Logging (Loguru)

```python
from loguru import logger

logger.info("Server starting...")
logger.error("Failed to connect: {err}", err=e)
logger.debug("Audio chunk size: {size}", size=len(audio))
```

### Error Handling in WebSocket

```python
try:
    async for message in websocket.iter_text():
        # Process
        await websocket.send_json({"status": "ok"})
except WebSocketDisconnect:
    logger.info("Client disconnected")
except Exception as e:
    logger.error("Error: {}", e)
    await websocket.send_json({"error": str(e)})
```

### Environment Variable Naming

- Use **OPENCLAW_** prefix for all settings
- Use snake_case: `OPENCLAW_STT_MODEL`, `OPENCLAW_GATEWAY_URL`
- Backend vars: `OPENAI_API_KEY`, `ALI_BAILIAN_API_KEY` (without prefix)

---

## 🚀 Common Tasks

### Add a New AI Backend

1. Create handler in [src/server/backend.py](../src/server/backend.py)
2. Add to `_setup_client()` method
3. Implement `chat_stream()` async generator
4. Add env var to [src/server/main.py](../src/server/main.py) Settings
5. Test with WebSocket client

### Integrate a New TTS Provider

1. Create `src/server/your_tts.py`
2. Extend class with `synthesize(text) → AsyncGenerator[bytes]`
3. Update [src/server/main.py](../src/server/main.py) to instantiate
4. Ensure audio format matches browser expectations (PCM, 44.1kHz)
5. Add tests in `tests/`

### Deploy to Production

```bash
# Using Docker
docker build -f Dockerfile -t openclaw-voice:latest .
docker run -e OPENCLAW_PORT=8765 \
           -e OPENAI_API_KEY=$KEY \
           -e OPENCLAW_REQUIRE_AUTH=true \
           -p 8765:8765 \
           openclaw-voice:latest

# Or use docker-compose
OPENCLAW_REQUIRE_AUTH=true docker compose up -d
```

---

## ⚠️ Common Pitfalls & Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| **WebSocket connection fails** | Server not running / different port | Check `OPENCLAW_PORT`, ensure server running: `python -m src.server.main` |
| **No audio transcription** | STT API key missing / model unavailable | Set `ALI_BAILIAN_API_KEY` or `OPENAI_API_KEY`; verify model name |
| **TTS audio not playing** | Incorrect audio format / codec mismatch | Ensure 16kHz PCM; check browser DevTools audio context |
| **High latency** | Large Whisper model / slow backend | Use `qwen3-asr-flash` for STT; enable streaming TTS |
| **CORS errors (frontend)** | Browser blocking requests | Server handles CORS; ensure StaticFiles mounted correctly |
| **Import errors** | Missing dependencies | Run `pip install -r requirements.txt` + `pip install .[dev]` |

---

## 📚 Additional Resources

- **README**: [README.md](../README.md) - Full features, configuration tables
- **TODOs**: [TODOS.md](../TODOS.md) - Current work items (streaming subtitles, WebSocket STT)
- **Tests**: [tests/](../tests/) - Examples of WebSocket testing with `pytest-asyncio`
- **Docker**: [docker-compose.yml](../docker-compose.yml) - Full stack (gateway + voice)

---

## 💡 Development Tips

1. **Keep responses concise**: System prompt encourages 1-2 sentence responses for fast streaming TTS
2. **Test locally first**: Use `--reload` flag with `uvicorn` for hot reload
3. **Check browser console**: Most audio issues show up in DevTools
4. **Use loguru for debugging**: `logger.debug()` outputs to console with context
5. **Stream early, buffer late**: TPS streaming starts after first sentence detected
6. **Handle WebSocket gracefully**: Always catch `WebSocketDisconnect` + implement reconnect logic

---

## 🔑 Key Modules Explained

### AIBackend (src/server/backend.py)

Abstraction for different AI providers. Automatically selects:
1. OpenClaw Gateway (if `OPENCLAW_GATEWAY_URL` + `OPENCLAW_GATEWAY_TOKEN`)
2. OpenAI (if `OPENAI_API_KEY`)
3. Bailian (if `ALI_BAILIAN_API_KEY`)

All use OpenAI-compatible API format for consistency.

### WebSocket Protocol (src/server/main.py)

```json
// Client → Server (browser audio chunk)
{"type": "audio", "data": "base64-encoded-audio"}

// Server → Client (AI response substring)
{"type": "message", "text": "Hello"}

// Server → Client (audio chunk)
{"type": "audio", "data": "base64-encoded-audio"}

// Server → Client (metadata)
{"type": "status", "status": "listening|processing|speaking"}
```

### Sentence-Level Streaming

TTS doesn't wait for full response; instead:
1. AI generates text token-by-token
2. Backend accumulates until period/newline detected
3. Sends complete sentence to TTS
4. TTS streams audio while AI continues generating
→ Perceived response time = avg(STT + TTS) instead of TTS alone

---

## 📝 Notes for Contributors

- **Coding Style**: Follow PEP 8 (use `black` and `ruff`)
- **Async-First**: All I/O should be async (`asyncio`, `aiohttp`, `httpx`)
- **Configuration**: Use environment variables with `OPENCLAW_` prefix
- **Error Handling**: Always catch exceptions in WebSocket handlers
- **Testing**: Test async code with `pytest-asyncio`
- **Documentation**: Update docstrings and environment variable tables
