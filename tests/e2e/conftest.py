"""
Shared fixtures and utilities for E2E backend tests.

All live tests require ALI_BAILIAN_API_KEY to be set:
  ALI_BAILIAN_API_KEY=sk-... pytest tests/e2e/ -v

Fixtures are function-scoped to prevent aiohttp session closure.
Logs are written to tests/e2e/test_run.log in real-time.
"""

import asyncio
import json
import os
import sys
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pytest
from loguru import logger as _base_logger

# Configure loguru for file-based logging in real-time
_log_dir = Path(__file__).parent
_log_file = _log_dir / "test_run.log"

# Remove default handler and add file handler
_base_logger.remove()
_base_logger.add(
    sys.stderr,
    level="DEBUG",
    format="<level>{time:HH:mm:ss}</level> | <level>{level: <8}</level> | {message}",
)
_base_logger.add(
    str(_log_file),
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    rotation="50 MB",  # rotate at 50MB
    compression="zip",  # compress rotated files
)

logger = _base_logger

# Make sure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# ── Audio constants ───────────────────────────────────────────────────────────
# Qwen-TTS Flash default output format (PCM, SSE streaming mode)
TTS_SAMPLE_RATE = 24000
TTS_CHANNELS = 1
TTS_SAMPWIDTH = 2  # 16-bit

# Test scenarios: key → (text, language)
SCENARIOS = {
    "short_zh":  ("你好，今天天气怎么样？", "zh"),
    "short_en":  ("Hello, how are you today?", "en"),
    "medium_zh": ("请简单介绍一下中国的四大发明。", "zh"),
    "medium_en": ("Tell me a brief interesting fact about the solar system.", "en"),
}


# ── LatencyTracker ────────────────────────────────────────────────────────────

@dataclass
class _Record:
    name: str
    duration_ms: float
    metadata: Dict = field(default_factory=dict)


class LatencyTracker:
    """
    Thread-safe accumulator for latency measurements.

    All measurements are logged to test_run.log in real-time for live monitoring.

    Usage::

        tracker.record("stt_latency", 420.3, scenario="short_zh")
        ...
        tracker.print_report()
        tracker.save_json("tests/e2e/performance_report.json")
    """

    def __init__(self) -> None:
        self._records: List[_Record] = []
        logger.info("=" * 80)
        logger.info("OPENCLAW VOICE — E2E BACKEND PERFORMANCE TEST SESSION STARTED")
        logger.info("=" * 80)

    def record(self, name: str, duration_ms: float, **metadata) -> None:
        self._records.append(_Record(name=name, duration_ms=duration_ms, metadata=metadata))
        meta_str = " | ".join(f"{k}={v}" for k, v in metadata.items())
        logger.info(f"⏱️  PERF: {name:30s} = {duration_ms:8.1f} ms  | {meta_str}")

    def summary(self) -> Dict:
        by_name: Dict[str, List[float]] = {}
        for r in self._records:
            by_name.setdefault(r.name, []).append(r.duration_ms)
        return {
            name: {
                "count": len(vals),
                "min_ms": round(min(vals), 1),
                "max_ms": round(max(vals), 1),
                "avg_ms": round(sum(vals) / len(vals), 1),
                "samples_ms": [round(v, 1) for v in vals],
            }
            for name, vals in by_name.items()
        }

    def print_report(self) -> None:
        summary = self.summary()
        sep = "─" * 72
        logger.info(f"\n{sep}")
        logger.info("  OPENCLAW VOICE — BACKEND PERFORMANCE REPORT")
        logger.info(sep)
        col = "{:<36}  {:>9}  {:>9}  {:>9}  {:>5}"
        logger.info(col.format("Metric", "Min (ms)", "Avg (ms)", "Max (ms)", "N"))
        logger.info(sep)
        for name, s in sorted(summary.items()):
            logger.info(col.format(name, s["min_ms"], s["avg_ms"], s["max_ms"], s["count"]))
        logger.info(sep)

    def save_json(self, path: str) -> None:
        data = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metrics": self.summary(),
        }
        Path(path).write_text(json.dumps(data, indent=2))
        logger.info(f"\n✅ Performance report written → {path}")
        logger.info(f"\n📊 For live logs during test execution, see → tests/e2e/test_run.log")


# Module-level singleton – shared across all sessions
_tracker = LatencyTracker()


# ── Audio helpers (module-level, no fixtures needed) ─────────────────────────

def save_pcm_as_wav(pcm_bytes: bytes, path: str, sample_rate: int = TTS_SAMPLE_RATE) -> None:
    """Write raw 16-bit mono PCM data to a WAV file with proper headers."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(TTS_CHANNELS)
        wf.setsampwidth(TTS_SAMPWIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)


def save_audio_bytes(data: bytes, path: str, sample_rate: int = TTS_SAMPLE_RATE) -> None:
    """
    Save TTS output to disk.

    Detects whether ``data`` already carries a RIFF/WAV header and saves
    accordingly; otherwise wraps it in one.
    """
    if data[:4] == b"RIFF":
        Path(path).write_bytes(data)
    else:
        save_pcm_as_wav(data, path, sample_rate)


def read_wav_to_numpy(path: str) -> Tuple[np.ndarray, int]:
    """Read a WAV file and return (float32 array in [-1, 1], sample_rate)."""
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    audio_int16 = np.frombuffer(raw, dtype=np.int16)
    return audio_int16.astype(np.float32) / 32768.0, sr


def duration_from_wav(path: str) -> float:
    """Return duration in seconds of a WAV file."""
    with wave.open(path, "rb") as wf:
        return wf.getnframes() / wf.getframerate()


async def collect_tts_stream(
    tts_client,
    text: str,
) -> Tuple[bytes, Optional[float], float]:
    """
    Drive ``BailianTTS.synthesize(stream=True)`` and return:
    ``(raw_pcm_bytes, first_chunk_ms, total_ms)``

    Measures wall-clock from the first API call to last byte received.
    Logs each chunk arrival for fine-grained monitoring.
    """
    chunks: List[bytes] = []
    first_chunk_ms: Optional[float] = None
    t0 = time.perf_counter()
    chunk_num = 0

    logger.debug(f"🔊 TTS: Starting stream for text: {text[:60]!r}...")
    async for chunk in tts_client.synthesize(text, stream=True):
        elapsed_ms = (time.perf_counter() - t0) * 1000
        chunk_num += 1
        if first_chunk_ms is None:
            first_chunk_ms = elapsed_ms
            logger.info(f"🔊 TTS: First audio chunk arrived at {first_chunk_ms:.1f}ms")
        chunks.append(chunk)
        logger.debug(f"🔊 TTS: Chunk #{chunk_num}: {len(chunk):,} bytes at {elapsed_ms:.1f}ms")

    total_ms = (time.perf_counter() - t0) * 1000
    total_bytes = sum(len(c) for c in chunks)
    logger.info(f"🔊 TTS: Complete in {total_ms:.1f}ms ({chunk_num} chunks, {total_bytes:,} bytes)")
    return b"".join(chunks), first_chunk_ms, total_ms


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def latency_tracker() -> LatencyTracker:
    return _tracker


@pytest.fixture(scope="session", autouse=True)
def save_report_on_exit(latency_tracker):
    """After the full test session, write the JSON performance report and summary to logs."""
    yield
    logger.info("\n" + "=" * 80)
    logger.info("TEST SESSION COMPLETE - GENERATING FINAL REPORT")
    logger.info("=" * 80)
    report_path = Path(__file__).parent / "performance_report.json"
    latency_tracker.print_report()
    latency_tracker.save_json(str(report_path))
    logger.info("=" * 80)


@pytest.fixture(scope="session")
def api_key() -> str:
    key = os.getenv("ALI_BAILIAN_API_KEY")
    if not key:
        pytest.skip(
            "ALI_BAILIAN_API_KEY is not set – skipping live E2E tests.\n"
            "Run with:  ALI_BAILIAN_API_KEY=sk-... pytest tests/e2e/ -v"
        )
    return key


@pytest.fixture(scope="session")
def audio_fixtures_dir() -> Path:
    d = Path(__file__).parent / "fixtures" / "audio"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture(scope="function")
async def tts_client(api_key):
    from src.server.bailian_tts import BailianTTS
    client = BailianTTS(api_key=api_key, model="qwen3-tts-flash", voice="Cherry")
    yield client
    await client.close()


@pytest.fixture(scope="function")
def stt_client(api_key):
    from src.server.bailian_stt import BailianSTT
    return BailianSTT(api_key=api_key, model="qwen3-asr-flash", language="zh")


# ── Pytest hooks for test lifecycle logging ───────────────────────────────────

def pytest_runtest_setup(item):
    """Log when a test starts."""
    logger.info(f"\n{'='*80}")
    logger.info(f"▶️  TEST START: {item.nodeid}")
    logger.info(f"{'='*80}")


def pytest_runtest_logreport(report):
    """Log test completion with pass/fail status and duration."""
    if report.when == "call":  # Only log the actual test execution, not setup/teardown
        if report.passed:
            logger.info(f"✅ TEST PASSED: {report.nodeid} ({report.duration*1000:.0f}ms)")
        elif report.failed:
            logger.error(f"❌ TEST FAILED: {report.nodeid} ({report.duration*1000:.0f}ms)")
        elif report.skipped:
            logger.warning(f"⊘  TEST SKIPPED: {report.nodeid}")


@pytest.fixture(scope="function")
async def llm_client(api_key):
    from src.server.backend import AIBackend
    client = AIBackend(
        backend_type="openai",
        url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-turbo",
        api_key=api_key,
        system_prompt=(
            "You are a helpful voice assistant. "
            "Keep responses concise and conversational — "
            "aim for 1-2 sentences unless more detail is requested."
        ),
    )
    yield client
    await client.close()


@pytest.fixture(scope="function")
async def audio_fixtures(api_key, audio_fixtures_dir, tts_client) -> Dict[str, Dict]:
    """
    Generate (or reuse cached) WAV audio fixtures for every scenario.

    Returns a dict:
    ``{"short_zh": {"path": "...", "text": "...", "language": "zh"}, ...}``

    Files are stored under ``tests/e2e/fixtures/audio/`` and
    regenerated only when missing so repeated runs are fast.
    """
    result: Dict[str, Dict] = {}

    for key, (text, language) in SCENARIOS.items():
        path = str(audio_fixtures_dir / f"{key}.wav")
        if os.path.exists(path):
            logger.info(f"[fixture] reusing cached {key}.wav")
        else:
            logger.info(f"[fixture] generating {key}.wav via TTS …")
            chunks: List[bytes] = []
            async for chunk in tts_client.synthesize(text, stream=True):
                chunks.append(chunk)
            if chunks:
                save_pcm_as_wav(b"".join(chunks), path)
                logger.info(f"[fixture] saved {key}.wav ({os.path.getsize(path):,} bytes)")
            else:
                logger.warning(f"[fixture] TTS returned no audio for {key}")
                continue
        result[key] = {"path": path, "text": text, "language": language}

    return result
