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

**For EVERY change, follow this order:**

1. **Write tests FIRST** - Tests must pass before proceeding
2. **Run smoke test** - `python scripts/smoke_test_agent.py`
3. **Run unit tests** - `pytest tests/unit/agent/ -v`
4. **Run linter** - `ruff check src/server/agent/ src/server/voice_turn.py`
5. **Run code review** - Use the `/speckit.review` command to review changes
6. **Commit** - Only after all above steps pass

**Checklist:**

- [ ] Code compiles: `python -c "import src.server.agent; import src.server.voice_turn"`
- [ ] New code has unit tests in `tests/unit/agent/`
- [ ] Tests written BEFORE or IMMEDIATELY AFTER implementation
- [ ] Smoke test passes: `python scripts/smoke_test_agent.py`
- [ ] Unit tests pass: `pytest tests/unit/agent/ -v`
- [ ] Lint passes: `ruff check src/server/agent/ src/server/voice_turn.py`
- [ ] Code review completed via `/speckit.review`
- [ ] Commit is atomic (one feature/fix per commit)
- [ ] Commit message follows: `type(scope): short description` format

## Recent Changes

- 001-agent-layer: Added Python 3.10+ + langchain, langchain-openai, langchain-agents

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
