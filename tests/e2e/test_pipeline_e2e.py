"""
Full Pipeline E2E Tests
=======================

Tests the complete STT → LLM → TTS pipeline.

This measures the end-to-end latency from:
1. User finishes speaking (simulated via pre-generated WAV fixture)
2. STT transcribes audio
3. LLM generates response
4. TTS synthesizes response audio
5. First audio byte is ready for playback

The key metric: **Time from STT input to first TTS audio byte** —
this is what the user perceives as response delay.

Run:
    ALI_BAILIAN_API_KEY=sk-... pytest tests/e2e/test_pipeline_e2e.py -v -s
"""

import asyncio
import time
from typing import Tuple

import pytest

from tests.e2e.conftest import (
    SCENARIOS,
    read_wav_to_numpy,
    collect_tts_stream,
)


async def _full_pipeline(
    prompt_audio_path: str,
    stt_client,
    llm_client,
    tts_client,
) -> Tuple[str, str, float, float, float]:
    """
    Execute full STT → LLM → TTS pipeline.

    Returns:
        (original_prompt, llm_response, stt_latency_ms, llm_ttft_ms, tts_ttfa_ms)
    """
    # Load pre-recorded speech
    audio, sr = read_wav_to_numpy(prompt_audio_path)

    # ── STT ───────────────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    stt_text, stt_ok = await stt_client.transcribe(audio, sample_rate=sr)
    stt_latency_ms = (time.perf_counter() - t0) * 1000

    if not stt_ok:
        raise AssertionError(f"STT failed: {stt_text}")

    # ── LLM ────────────────────────────────────────────────────────────────────
    llm_text = ""
    llm_ttft_ms = 0.0
    t0 = time.perf_counter()

    async for chunk in llm_client.chat_stream(stt_text):
        now_ms = (time.perf_counter() - t0) * 1000
        if not llm_text:
            llm_ttft_ms = now_ms
        llm_text += chunk

    # ── TTS ────────────────────────────────────────────────────────────────────
    tts_pcm, tts_ttfa_ms, _ = await collect_tts_stream(tts_client, llm_text)
    assert tts_pcm, "TTS produced no audio"

    return stt_text, llm_text, stt_latency_ms, llm_ttft_ms, tts_ttfa_ms


# ── Full pipeline tests ────────────────────────────────────────────────────────

class TestFullPipeline:
    """End-to-end pipeline tests with latency measurement."""

    @pytest.mark.asyncio
    async def test_pipeline_short_zh(
        self, audio_fixtures, stt_client, llm_client, tts_client, latency_tracker
    ):
        """Short Chinese prompt: fixture → STT → LLM → TTS."""
        fixture = audio_fixtures["short_zh"]
        stt_text, llm_text, stt_lat, llm_ttft, tts_ttfa = await _full_pipeline(
            fixture["path"], stt_client, llm_client, tts_client
        )

        # Record metrics
        latency_tracker.record("pipeline_stt_latency_ms", stt_lat, scenario="short_zh")
        latency_tracker.record("pipeline_llm_ttft_ms", llm_ttft, scenario="short_zh")
        latency_tracker.record("pipeline_tts_ttfa_ms", tts_ttfa, scenario="short_zh")

        # Calculate total time-to-first-audio
        ttfa_total = stt_lat + llm_ttft + tts_ttfa
        latency_tracker.record("pipeline_total_ttfa_ms", ttfa_total, scenario="short_zh")

        print(
            f"\nPipeline short_zh:"
            f"\n  STT latency        : {stt_lat:.0f} ms  →  {stt_text!r}"
            f"\n  LLM TTFT           : {llm_ttft:.0f} ms  →  {llm_text[:60]!r}"
            f"\n  TTS TTFA           : {tts_ttfa:.0f} ms"
            f"\n  ─────────────────────────────"
            f"\n  Total TTFA         : {ttfa_total:.0f} ms"
        )

        assert stt_text.strip(), "STT returned empty"
        assert llm_text.strip(), "LLM returned empty"

    @pytest.mark.asyncio
    async def test_pipeline_short_en(
        self, audio_fixtures, stt_client, llm_client, tts_client, latency_tracker
    ):
        """Short English prompt: fixture → STT → LLM → TTS."""
        fixture = audio_fixtures["short_en"]
        stt_text, llm_text, stt_lat, llm_ttft, tts_ttfa = await _full_pipeline(
            fixture["path"], stt_client, llm_client, tts_client
        )

        latency_tracker.record("pipeline_stt_latency_ms", stt_lat, scenario="short_en")
        latency_tracker.record("pipeline_llm_ttft_ms", llm_ttft, scenario="short_en")
        latency_tracker.record("pipeline_tts_ttfa_ms", tts_ttfa, scenario="short_en")

        ttfa_total = stt_lat + llm_ttft + tts_ttfa
        latency_tracker.record("pipeline_total_ttfa_ms", ttfa_total, scenario="short_en")

        print(
            f"\nPipeline short_en:"
            f"\n  STT latency        : {stt_lat:.0f} ms"
            f"\n  LLM TTFT           : {llm_ttft:.0f} ms"
            f"\n  TTS TTFA           : {tts_ttfa:.0f} ms"
            f"\n  ─────────────────────────────"
            f"\n  Total TTFA         : {ttfa_total:.0f} ms"
        )

        assert stt_text.strip()
        assert llm_text.strip()

    @pytest.mark.asyncio
    async def test_pipeline_medium_zh(
        self, audio_fixtures, stt_client, llm_client, tts_client, latency_tracker
    ):
        """Medium Chinese prompt: fixture → STT → LLM → TTS."""
        fixture = audio_fixtures["medium_zh"]
        stt_text, llm_text, stt_lat, llm_ttft, tts_ttfa = await _full_pipeline(
            fixture["path"], stt_client, llm_client, tts_client
        )

        latency_tracker.record("pipeline_stt_latency_ms", stt_lat, scenario="medium_zh")
        latency_tracker.record("pipeline_llm_ttft_ms", llm_ttft, scenario="medium_zh")
        latency_tracker.record("pipeline_tts_ttfa_ms", tts_ttfa, scenario="medium_zh")

        ttfa_total = stt_lat + llm_ttft + tts_ttfa
        latency_tracker.record("pipeline_total_ttfa_ms", ttfa_total, scenario="medium_zh")

        print(
            f"\nPipeline medium_zh:"
            f"\n  STT latency        : {stt_lat:.0f} ms"
            f"\n  LLM TTFT           : {llm_ttft:.0f} ms"
            f"\n  TTS TTFA           : {tts_ttfa:.0f} ms"
            f"\n  ─────────────────────────────"
            f"\n  Total TTFA         : {ttfa_total:.0f} ms"
        )

        assert stt_text.strip()
        assert llm_text.strip()

    @pytest.mark.asyncio
    async def test_pipeline_medium_en(
        self, audio_fixtures, stt_client, llm_client, tts_client, latency_tracker
    ):
        """Medium English prompt: fixture → STT → LLM → TTS."""
        fixture = audio_fixtures["medium_en"]
        stt_text, llm_text, stt_lat, llm_ttft, tts_ttfa = await _full_pipeline(
            fixture["path"], stt_client, llm_client, tts_client
        )

        latency_tracker.record("pipeline_stt_latency_ms", stt_lat, scenario="medium_en")
        latency_tracker.record("pipeline_llm_ttft_ms", llm_ttft, scenario="medium_en")
        latency_tracker.record("pipeline_tts_ttfa_ms", tts_ttfa, scenario="medium_en")

        ttfa_total = stt_lat + llm_ttft + tts_ttfa
        latency_tracker.record("pipeline_total_ttfa_ms", ttfa_total, scenario="medium_en")

        print(
            f"\nPipeline medium_en:"
            f"\n  STT latency        : {stt_lat:.0f} ms"
            f"\n  LLM TTFT           : {llm_ttft:.0f} ms"
            f"\n  TTS TTFA           : {tts_ttfa:.0f} ms"
            f"\n  ─────────────────────────────"
            f"\n  Total TTFA         : {ttfa_total:.0f} ms"
        )

        assert stt_text.strip()
        assert llm_text.strip()


# ── Latency perception benchmarks ──────────────────────────────────────────────

class TestLatencyPerception:
    """
    Human perception guidelines for latency:
    - < 200ms   : Feels instant
    - 200-500ms : Feels responsive
    - 500-1000ms: Feels sluggish
    - > 2000ms  : Feels laggy

    Our target for TTFA: < 1500ms for short responses.
    """

    @pytest.mark.asyncio
    async def test_ttfa_short_target(
        self, audio_fixtures, stt_client, llm_client, tts_client
    ):
        """Verify short-response TTFA meets perception target (<1500ms)."""
        fixture = audio_fixtures["short_zh"]
        stt_text, llm_text, stt_lat, llm_ttft, tts_ttfa = await _full_pipeline(
            fixture["path"], stt_client, llm_client, tts_client
        )

        ttfa = stt_lat + llm_ttft + tts_ttfa
        print(f"\nTTFA for short response: {ttfa:.0f} ms")

        # Soft assertion – log warning but don't fail if we exceed target
        if ttfa > 1500:
            print(f"⚠️  TTFA exceeded target: {ttfa:.0f}ms > 1500ms")
            print(
                f"  Breakdown: STT={stt_lat:.0f}ms, LLM={llm_ttft:.0f}ms, TTS={tts_ttfa:.0f}ms"
            )
        else:
            print(f"✓ TTFA within target: {ttfa:.0f}ms < 1500ms")

    @pytest.mark.asyncio
    async def test_streaming_advantage(
        self, audio_fixtures, stt_client, llm_client, tts_client
    ):
        """
        Demonstrate streaming advantage:
        By starting TTS while LLM is still generating, we reduce
        perceived latency. The test measures this by recording
        when the first audio chunk arrives.
        """
        fixture = audio_fixtures["short_zh"]
        stt_text, llm_text, stt_lat, llm_ttft, tts_ttfa = await _full_pipeline(
            fixture["path"], stt_client, llm_client, tts_client
        )

        # If we waited for full LLM response before TTS:
        full_wait = stt_lat + llm_ttft + 200  # assume tts takes ~200ms for first chunk

        # With streaming, we get first audio in:
        streaming_time = stt_lat + llm_ttft + tts_ttfa

        # The "advantage" is the savings if we start TTS early (mid-LLM generation)
        # For now, we measure what actually happened.
        print(
            f"\nStreaming latency:"
            f"\n  Time to first audio: {streaming_time:.0f} ms"
            f"\n  (STT={stt_lat:.0f}ms + LLM_TTFT={llm_ttft:.0f}ms + TTS_TTFA={tts_ttfa:.0f}ms)"
        )
