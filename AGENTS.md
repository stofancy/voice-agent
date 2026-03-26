# voice-agent Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-25

## Active Technologies

- Python 3.10+ + langchain, langchain-openai, langchain-agents (001-agent-layer)

## Project Structure

```text
src/
tests/
```

## Commands

```bash
# Install dependencies (modern pyproject.toml)
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
```

## Code Style

Python 3.10+: Follow standard conventions

## Recent Changes

- 001-agent-layer: Added Python 3.10+ + langchain, langchain-openai, langchain-agents

## Incremental Commit Checklist

**Before every commit, verify:**

- [ ] Code compiles: `python -c "import src.server.agent; import src.server.voice_turn"`
- [ ] New code has unit tests in `tests/unit/agent/`
- [ ] Tests written BEFORE or IMMEDIATELY AFTER implementation
- [ ] Run tests: `pytest tests/unit/agent/ -v` (skip if langchain-core not installed)
- [ ] Run linter: `ruff check src/server/agent/ src/server/voice_turn.py`
- [ ] Commit is atomic (one feature/fix per commit)
- [ ] Commit message follows: `type(scope): short description` format

## Recent Changes

- 001-agent-layer: Added Python 3.10+ + langchain, langchain-openai, langchain-agents

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
