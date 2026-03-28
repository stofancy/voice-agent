# Voice Agent Developer Guidelines

## Core Principles for AI Collaboration

### 1. Evidence-Based Responses (NON-NEGOTIABLE)
- **Never speculate** - when uncertain, say "I don't know" and research
- When answering technical questions, **cite sources** or provide empirical evidence
- If **web search** is needed, perform it - do not hallucinate facts
- Preferences: docs > code > intuition

### 2. Communication Style
- Direct and concise - avoid unnecessary preamble
- Distinguish between: fact, reasoned opinion, speculation
- Ask clarifying questions when requirements are ambiguous

### 3. Technical Rigor
- Verify claims against source code, docs, or external references
- Acknowledge knowledge boundaries
- Provide working code/examples when possible

## Project-Specific Context

### Architecture
```
Browser → STT → [Self-built Agent Layer] → TTS/Stream → Browser
                      ↑
                Multiple specialized agents
                (booking/hotel/query...)
```

### Current Goal
Replace OpenClaw agent dependency with custom agent layer to:
- Control streaming behavior (especially during tool calls)
- Enable multi-agent orchestration
- Flexible output to TTS and frontend

## Tech Stack

- **Language**: Python 3.10+
- **WebSocket**: FastAPI / uvicorn
- **STT**: Alibaba Bailian Qwen-ASR
- **TTS**: Alibaba Bailian Qwen-TTS (streaming)
- **LLM**: OpenAI-compatible API (self-managed, not OpenClaw)

## Framework Preference
**Lightweight over heavy abstractions** - this is an exploratory MVP
