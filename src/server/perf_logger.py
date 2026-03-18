"""
Performance logging module for Voice Agent.

Collects round-trip timing data from frontend and backend,
merges timestamps, computes derived metrics, and writes to logs/performance.jsonl.
"""

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger


# Module-level enabled flag — read once at import time
_PERF_ENABLED: bool = os.getenv("OPENCLAW_PERF_LOGGING", "false").lower() == "true"

# Lazy-open file handle (None when disabled)
_log_file: Optional[Any] = None


def is_enabled() -> bool:
    """Return whether perf logging is enabled."""
    return _PERF_ENABLED


def _get_log_path() -> Path:
    """Return the log file path, creating logs/ dir if needed."""
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / "performance.jsonl"


def _open_log_file():
    """Lazily open the JSONL log file."""
    global _log_file
    if _log_file is None:
        log_path = _get_log_path()
        _log_file = open(log_path, "a", buffering=1)  # line-buffered
        logger.debug(f"[perf_logger] Logging to {log_path}")


def log_round(
    frontend_data: dict,
    backend_data: dict,
    context: Optional[dict] = None,
) -> Optional[str]:
    """
    Merge frontend + backend timestamps, compute derived metrics, write JSONL.

    Args:
        frontend_data: {
            "button_release_to_transcript_ms": float,
            "button_release_to_first_subtitle_ms": float | None,
            "button_release_to_first_audio_received_ms": float | None,
            "button_release_to_first_audio_played_ms": float | None,
            "button_release_to_tts_end_ms": float | None,
        }
        backend_data: {
            "stt_ms": float,
            "llm_ttft_ms": float,
            "llm_gen_ms": float,
            "tts_ttfa_ms": float,
            "tts_total_ms": float,
        }
        context: {
            "transcript": str,
            "response_length": int,
            "tts_model": str,
            "llm_model": str,
            "tts_voice": str,
            "audio_chunks_count": int,
            "audio_bytes_total": int,
        }

    Returns:
        round_id (uuid) if logged, None if disabled.
    """
    if not _PERF_ENABLED:
        return None

    try:
        _open_log_file()

        round_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

        fe = frontend_data or {}
        be = backend_data or {}

        # Computed metrics
        fe_e2e = fe.get("button_release_to_first_audio_played_ms")
        be_e2e = (
            be.get("stt_ms", 0)
            + be.get("llm_gen_ms", 0)
            + be.get("tts_total_ms", 0)
        )

        if fe_e2e is not None:
            network_overhead_ms = fe_e2e - be_e2e
        else:
            network_overhead_ms = None

        audio_render_delay_ms: Optional[float] = None
        if fe.get("button_release_to_first_audio_played_ms") is not None and fe.get(
            "button_release_to_first_audio_received_ms"
        ) is not None:
            audio_render_delay_ms = (
                fe["button_release_to_first_audio_played_ms"]
                - fe["button_release_to_first_audio_received_ms"]
            )

        user_perceived_e2e_ms = fe.get("button_release_to_first_audio_played_ms")

        record = {
            "timestamp": ts,
            "round_id": round_id,
            "frontend": {
                "button_release_to_transcript_ms": fe.get("button_release_to_transcript_ms"),
                "button_release_to_first_subtitle_ms": fe.get(
                    "button_release_to_first_subtitle_ms"
                ),
                "button_release_to_first_audio_received_ms": fe.get(
                    "button_release_to_first_audio_received_ms"
                ),
                "button_release_to_first_audio_played_ms": fe.get(
                    "button_release_to_first_audio_played_ms"
                ),
                "button_release_to_tts_end_ms": fe.get("button_release_to_tts_end_ms"),
            },
            "backend": {
                "stt_ms": be.get("stt_ms"),
                "llm_ttft_ms": be.get("llm_ttft_ms"),
                "llm_gen_ms": be.get("llm_gen_ms"),
                "tts_ttfa_ms": be.get("tts_ttfa_ms"),
                "tts_total_ms": be.get("tts_total_ms"),
            },
            "computed": {
                "network_overhead_ms": round(network_overhead_ms, 2)
                if network_overhead_ms is not None
                else None,
                "audio_render_delay_ms": round(audio_render_delay_ms, 2)
                if audio_render_delay_ms is not None
                else None,
                "user_perceived_e2e_ms": round(user_perceived_e2e_ms, 2)
                if user_perceived_e2e_ms is not None
                else None,
            },
            "context": context or {},
        }

        line = json.dumps(record, ensure_ascii=False)
        _log_file.write(line + "\n")
        _log_file.flush()

        logger.debug(f"[perf_logger] Round logged: {round_id}")
        return round_id

    except Exception as e:
        logger.error(f"[perf_logger] Failed to write perf log: {e}")
        return None
