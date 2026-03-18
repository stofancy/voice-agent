# GitHub Copilot Instructions - OpenClaw Voice

## Project Overview

OpenClaw Voice is a real-time voice conversation system with:
- **Backend**: Python FastAPI (STT/TTS/LLM orchestration)
- **Frontend**: React + Vite + TypeScript
- **Gateway**: OpenClaw Gateway (Docker container)

## Development Commands

### Local Development (Recommended)

```bash
# Terminal 1: Start backend (port 8766)
cd ~/workspaces/voice-agent
source .venv/bin/activate
python -m uvicorn src.server.main:app --host 0.0.0.0 --port 8766 --reload

# Terminal 2: Start frontend (port 5173)
cd ~/workspaces/voice-agent/src/client/v2-react
npm run dev
```

**Access**:
- Frontend: http://localhost:5173/v2/
- Backend API: http://localhost:8766/
- Health: http://localhost:8766/health

### Production Deployment

```bash
cd ~/workspaces/voice-agent
./scripts/deploy.sh
```

**Access**:
- Frontend: http://localhost:8764/
- Backend: http://localhost:8765/

## Key Files

| File | Purpose |
|------|---------|
| `src/server/main.py` | FastAPI backend entry point |
| `src/client/v2-react/` | React frontend |
| `docker-compose.yml` | Production Docker config |
| `.env.local` | Local development env vars |
| `requirements.txt` | Python dependencies |
| `src/client/v2-react/package.json` | Node dependencies |

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frontend  │───→│   Backend   │───→│   Gateway   │
│  Vite :5173 │    │ Uvicorn :8766│    │ Docker :26523│
└─────────────┘    └─────────────┘    └─────────────┘
```

## Code Style

- **Python**: Type hints, async/await, loguru logging
- **TypeScript**: Strict mode, functional components, hooks
- **API**: RESTful + WebSocket for real-time audio

## Testing

```bash
# Backend health check
curl http://localhost:8766/health

# Frontend build
cd src/client/v2-react && npm run build
```

## Common Issues

1. **Port conflicts**: Backend uses 8766 (dev) / 8765 (prod)
2. **Gateway not running**: `docker compose up -d openclaw-gateway`
3. **Missing deps**: `pip install -r requirements.txt` or `npm install`

## Documentation

- `docs/DEVELOPMENT.md` - Full development guide
- `docs/AI_DEV_GUIDE.md` - AI assistant guidelines
- `README.md` - Project overview
