# Claude Code Instructions - OpenClaw Voice

## Project Context

This is a real-time voice conversation system built with:
- **Backend**: Python FastAPI with Bailian API (STT: qwen3-asr-flash, TTS: qwen3-tts-flash)
- **Frontend**: React 19 + Vite + TypeScript + TailwindCSS
- **Infrastructure**: Docker Compose (Gateway + Backend + Frontend)

**Location**: `~/workspaces/voice-agent/`

---

## Development Workflow

### 1. Local Development (Default)

**Start Backend** (Terminal 1):
```bash
cd ~/workspaces/voice-agent
source .venv/bin/activate
python -m uvicorn src.server.main:app --host 0.0.0.0 --port 8766 --reload
```

**Start Frontend** (Terminal 2):
```bash
cd ~/workspaces/voice-agent/src/client/v2-react
npm run dev
```

**Verify**:
- Frontend: http://localhost:5173/v2/
- Backend Health: http://localhost:8766/health

### 2. Production Deployment

```bash
cd ~/workspaces/voice-agent
./scripts/deploy.sh
```

---

## Key Configuration

### Environment Variables (`.env.local`)

```bash
# Required
OPENCLAW_BAILIAN_API_KEY=sk-xxx

# Backend
OPENCLAW_PORT=8766
OPENCLAW_STT_MODEL=qwen3-asr-flash
OPENCLAW_TTS_MODEL=qwen3-tts-flash
OPENCLAW_TTS_VOICE=Cherry

# Gateway (Docker)
OPENCLAW_GATEWAY_URL=http://localhost:26523
OPENCLAW_GATEWAY_TOKEN=openclaw-your-gateway-token-here
```

### Port Allocation

| Environment | Backend | Frontend | Gateway |
|-------------|---------|----------|---------|
| **Dev** | 8766 | 5173 | 26523 |
| **Prod** | 8765 | 8764 | 26523 |

---

## File Structure

```
voice-agent/
├── src/
│   ├── server/          # Python backend
│   │   ├── main.py      # FastAPI app
│   │   ├── bailian_stt.py
│   │   ├── bailian_tts.py
│   │   └── backend.py
│   └── client/v2-react/ # React frontend
│       ├── src/
│       ├── package.json
│       └── vite.config.ts
├── scripts/             # Shell scripts
├── docker-compose.yml   # Production deploy
├── .env.local           # Dev env vars
└── docs/                # Documentation
```

---

## Common Tasks

### Add Python Dependency
```bash
source .venv/bin/activate
pip install <package>
pip freeze >> requirements.txt
```

### Add Node Dependency
```bash
cd src/client/v2-react
npm install <package>
```

### Debug Gateway
```bash
docker compose logs -f openclaw-gateway
docker compose restart openclaw-gateway
```

### Health Checks
```bash
curl http://localhost:8766/health  # Backend
curl http://localhost:5173/v2/     # Frontend
```

---

## Code Conventions

### Python (Backend)
- Use type hints
- Async/await for I/O
- Loguru for logging
- Pydantic for settings validation

### TypeScript (Frontend)
- Strict mode enabled
- Functional components with hooks
- TailwindCSS for styling
- Framer Motion for animations

### API Design
- RESTful endpoints
- WebSocket for real-time audio (`/v2/ws`)
- Health check at `/health`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8766 occupied | `lsof -i :8766` then kill process |
| Gateway not responding | `docker compose ps` check status |
| Frontend build fails | `npm install` then retry |
| STT/TTS errors | Check Bailian API key in `.env.local` |

---

## Documentation

- `docs/DEVELOPMENT.md` - Complete development guide
- `docs/AI_DEV_GUIDE.md` - AI assistant guidelines
- `README.md` - Project overview

---

*Last updated: 2026-03-18*
