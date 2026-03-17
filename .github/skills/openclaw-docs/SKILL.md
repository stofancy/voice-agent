---
name: openclaw-docs
description: 'OpenClaw documentation retrieval skill. Use when: OpenClaw architecture, gateway/protocol, agent behavior, memory/tools/integrations, custom extensions/plugins, channels, providers, deployment, or troubleshooting. ALWAYS use this skill first for OpenClaw-specific questions before answering from general knowledge. Fetches markdown from https://docs.openclaw.ai/ for real-time documentation.'
argument-hint: 'What OpenClaw topic or task do you need help with? (e.g., "create a memory plugin", "debug agent loops", "understand gateway architecture")'
---

# OpenClaw Documentation & Learning Guide

OpenClaw is a comprehensive framework for building AI agents with memory, tools, and real-time communication. This skill provides access to the official documentation wiki and guidance for common development tasks.

## When to Use

- **Learning OpenClaw**: Understanding core concepts (memory, tools, gateway, extensions)
- **Creating Extensions**: Building custom memory backends, tool adapters, or plugin modules
- **Troubleshooting**: Debugging agent behavior, WebSocket issues, tool integration problems
- **Architecture Questions**: How memory persistence works, extension loading, tool execution flow
- **API Integration**: Connecting OpenClaw to external services, building custom backends
- **Best Practices**: Design patterns for agents, memory optimization, tool design

## How This Skill Works

This skill accesses the official OpenClaw documentation at **https://docs.openclaw.ai/**.

Use two index sources:

- Local snapshot (fast path): `./references/llms.snapshot.txt`
- Remote source of truth: `https://docs.openclaw.ai/llms.txt`

Start with the local snapshot for performance, then refresh from remote when needed.

Always keep the remote index available as the authoritative source:

- `https://docs.openclaw.ai/llms.txt` (authoritative page list for LLMs)

Then fetch specific pages from links in that index.

Any docs page can be fetched as markdown by appending `.md` to the URL.

**Example**: The page `https://docs.openclaw.ai/concepts/memory` is available as markdown at `https://docs.openclaw.ai/concepts/memory.md`, making it easy for AI to read and reference.

### Retrieval Strategy (Required)

1. Read `./references/llms.snapshot.txt` first (fast local discovery)
2. Find the most relevant page links for the user request
3. Refresh the snapshot from `https://docs.openclaw.ai/llms.txt` if any trigger occurs:
  - selected doc link returns 404/5xx or fails to fetch
  - no relevant concept/page is found in snapshot
  - user asks for newest/latest docs
  - topic appears renamed or moved
4. After refresh, re-select links from the updated index
5. Fetch 1-3 best matching `.md` pages
6. Synthesize answer from fetched docs (prefer direct docs wording when possible)
7. Provide follow-up links from the same index section

### Snapshot Refresh Rule

When refresh is needed, overwrite the local snapshot:

```bash
curl -fsSL https://docs.openclaw.ai/llms.txt -o .github/skills/openclaw-docs/references/llms.snapshot.txt
```

Treat the snapshot as a cache, not a permanent truth source.

## Common Tasks

### 1. Learn a Concept
```
User: "Explain OpenClaw memory concepts"
Procedure:
  1. Read ./references/llms.snapshot.txt
  2. Find concepts/memory link in the index
  3. If missing/broken, refresh snapshot from remote llms.txt and retry
  4. Fetch https://docs.openclaw.ai/concepts/memory.md
  5. Explain key components with examples
  6. Link related indexed pages (agent loop, session, tools)
```

### 2. Create a Custom Extension
```
User: "I need to create a memory plugin for Redis"
Procedure:
  1. Read ./references/llms.snapshot.txt
  2. Find plugin and memory backend pages from index entries
  3. If needed, refresh snapshot from remote llms.txt
  4. Fetch those exact pages (.md URLs from the index)
  5. Review lifecycle and interface requirements
  6. Provide code template with Redis integration example
  7. Link testing and deployment pages from index
```

### 3. Debug Agent Behavior
```
User: "My agent isn't remembering conversation context"
Procedure:
  1. Read ./references/llms.snapshot.txt
  2. Find relevant troubleshooting + memory concept pages
  3. If needed, refresh snapshot from remote llms.txt
  4. Fetch matching docs from index (for example, help/troubleshooting.md and concepts/memory.md)
  5. Identify root cause (persistence, loading, scope)
```

### 4. Understand Tool Integration
```
User: "How do I add a custom tool to my agent?"
Procedure:
  1. Read ./references/llms.snapshot.txt
  2. Find tools pages (e.g. tools/index.md, tools/creating-skills.md, tools/subagents.md)
  3. If needed, refresh snapshot from remote llms.txt
  4. Fetch the most relevant tool docs
  5. Review schema/execution/error handling details
  6. Provide working example with best practices
```

## Documentation Discovery

Use `llms.txt` as the source of truth for available pages, then route by section prefixes found in that file.

Common sections visible in the index include:

| Prefix | Typical Contents |
|------|----------|
| `/start/` | Getting started, setup, hubs, onboarding |
| `/concepts/` | Agent runtime, memory, sessions, architecture |
| `/gateway/` | Configuration, security, protocol, troubleshooting |
| `/tools/` | Tooling model, skills, sub-agents, tool behavior |
| `/plugins/` | Plugin docs and manifests |
| `/providers/` | Model provider integrations |
| `/channels/` | WhatsApp/Telegram/Discord and routing |
| `/help/` | FAQ, testing, troubleshooting |
| `/web/` | Control UI, dashboard, web chat |
| `/cli/` | Command reference |

## Useful Doc Pages (Reference)

Key pages confirmed in the index (`llms.txt`) for common tasks:

**Learning Basics**:
- `https://docs.openclaw.ai/start/getting-started.md`
- `https://docs.openclaw.ai/concepts/agent.md`
- `https://docs.openclaw.ai/concepts/memory.md`

**Tools & Skills**:
- `https://docs.openclaw.ai/tools/index.md`
- `https://docs.openclaw.ai/tools/creating-skills.md`
- `https://docs.openclaw.ai/tools/subagents.md`
- `https://docs.openclaw.ai/tools/skills.md`

**Gateway & Deployment**:
- `https://docs.openclaw.ai/gateway/index.md`
- `https://docs.openclaw.ai/gateway/configuration.md`
- `https://docs.openclaw.ai/gateway/protocol.md`
- `https://docs.openclaw.ai/gateway/troubleshooting.md`

**Troubleshooting**:
- `https://docs.openclaw.ai/help/troubleshooting.md`
- `https://docs.openclaw.ai/help/debugging.md`
- `https://docs.openclaw.ai/channels/troubleshooting.md`

## Procedure: Quick Start Guide

When a user asks for help with OpenClaw:

1. **Identify the topic**: Is this about memory, tools, extensions, architecture, or troubleshooting?
2. **Use local index cache first**: `./references/llms.snapshot.txt`
3. **Refresh cache from remote when needed**: `https://docs.openclaw.ai/llms.txt` (broken link/missing topic/latest request)
4. **Select relevant pages from index**: Prefer exact links from the index
5. **Fetch those pages as markdown**: Use `.md` URLs directly
6. **Synthesize information**: Combine official docs with project-specific context (OpenClaw Voice)
7. **Link to further resources**: Point to related docs discovered from index

## Context: OpenClaw Voice

The current project (OpenClaw Voice) is a browser-based voice interface for AI assistants built with:
- FastAPI WebSocket server (Python)
- Alibaba Bailian STT/TTS
- OpenClaw Gateway as AI backend
- Streaming sentence-by-sentence responses

Many OpenClaw docs concepts apply here:
- **Memory**: Conversation history management (see `/concepts/memory.md`)
- **Tools**: Custom tool integration (discover via `llms.snapshot.txt` under `/tools/`)
- **Gateway**: Server-side agent deployment (discover via `llms.snapshot.txt` under `/gateway/`)
- **Extensions**: Adding new STT/TTS backends as plugins

## Example Interactions

### User asks: "How do I add a new language to OpenClaw voice STT?"
1. Check OpenClaw tools/extensions docs
2. Review STT backend architecture
3. Find relevant `/tools/` pages from `./references/llms.snapshot.txt` (refresh if needed)
4. Provide code example for language-aware tool wrapper

### User asks: "Can I use OpenClaw memory with SQLite?"
1. Find memory + data integration docs from `./references/llms.snapshot.txt`
2. Refresh index from remote `llms.txt` if page is missing/broken
3. Provide working SQLite backend example
4. Link to testing and deployment guides

### User asks: "What's the OpenClaw Gateway protocol?"
1. Find gateway protocol docs from `./references/llms.snapshot.txt`
2. Refresh index from remote `llms.txt` if page is missing/broken
4. Link to gateway deployment in this project

## Tips for Effective Learning

1. **Start with concepts**: Read `/concepts/` pages for architecture understanding
2. **Then explore implementation**: Read `/architecture/` and `/extensions/` for deep dives
4. **Troubleshoot if needed**: Check `/troubleshooting/` when things don't work
5. **Link related topics**: Use cross-references in docs to build mental models

## Quick Reference: Markdown URL Pattern

Any page on https://docs.openclaw.ai/ can be accessed as markdown:

```
HTML:     https://docs.openclaw.ai/concepts/memory
Markdown: https://docs.openclaw.ai/concepts/memory.md
```

For discovery, always use:

```
Index: https://docs.openclaw.ai/llms.txt
Snapshot cache: ./references/llms.snapshot.txt
```

This allows the AI agent to:
- Fetch and parse documentation programmatically
- Provide real-time, up-to-date information
- Include relevant sections in responses
- Link to specific sections for further reading
