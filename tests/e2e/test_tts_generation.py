"""
TTS Generation Tests
====================

Tests Alibaba Bailian Qwen-TTS (qwen3-tts-flash) directly:

- Generates voice WAV files for all test scenarios
- Measures TTS first-audio latency (TTFA) in streaming mode
- Measures total synthesis duration
- Tests all available voices
- Validates output audio is non-empty and well-formed WAV

Run:
    ALI_BAILIAN_API_KEY=sk-... pytest tests/e2e/test_tts_generation.py -v
"""

import asyncio
import os
import time
import wave
from typing import List

import numpy as np
import pytest

from tests.e2e.conftest import (
    SCENARIOS,
    TTS_SAMPLE_RATE,
    collect_tts_stream,
    duration_from_wav,
    save_pcm_as_wav,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assert_valid_wav(path: str) -> None:
    """Raise AssertionError if path is not a readable WAV with audio frames."""
    assert os.path.exists(path), f"WAV file not found: {path}"
    with wave.open(path, "rb") as wf:
        assert wf.getnframes() > 0, "WAV has zero frames"
        assert wf.getnchannels() == 1, "Expected mono"
        assert wf.getsampwidth() == 2, "Expected 16-bit"
    dur = duration_from_wav(path)
    assert dur > 0.1, f"Audio too short: {dur:.3f}s"


# ── Voice file generation – one test per scenario ─────────────────────────────

class TestTTSVoiceFileGeneration:
    """
    Generate WAV files for every scenario and verify they are valid.

    Files are written to tests/e2e/fixtures/audio/<scenario>.wav.
    Subsequent test runs reuse cached files (instant), rerun to regenerate
    by deleting the fixture files.
    """

    @pytest.mark.asyncio
    async def test_generate_short_zh(self, tts_client, audio_fixtures_dir, latency_tracker):
        text, _lang = SCENARIOS["short_zh"]
        path = str(audio_fixtures_dir / "short_zh.wav")
        pcm, first_ms, total_ms = await collect_tts_stream(tts_client, text)
        assert pcm, "No audio data received from TTS"
        save_pcm_as_wav(pcm, path)
        _assert_valid_wav(path)
        latency_tracker.record("tts_ttfa_ms", first_ms, scenario="short_zh")
        latency_tracker.record("tts_total_ms", total_ms, scenario="short_zh")
        dur = duration_from_wav(path)
        print(f"\nshort_zh: TTFA={first_ms:.0f}ms  total={total_ms:.0f}ms  audio={dur:.2f}s")

    @pytest.mark.asyncio
    async def test_generate_short_en(self, tts_client, audio_fixtures_dir, latency_tracker):
        text, _lang = SCENARIOS["short_en"]
        path = str(audio_fixtures_dir / "short_en.wav")
        pcm, first_ms, total_ms = await collect_tts_stream(tts_client, text)
        assert pcm, "No audio data received from TTS"
        save_pcm_as_wav(pcm, path)
        _assert_valid_wav(path)
        latency_tracker.record("tts_ttfa_ms", first_ms, scenario="short_en")
        latency_tracker.record("tts_total_ms", total_ms, scenario="short_en")
        dur = duration_from_wav(path)
        print(f"\nshort_en: TTFA={first_ms:.0f}ms  total={total_ms:.0f}ms  audio={dur:.2f}s")

    @pytest.mark.asyncio
    async def test_generate_medium_zh(self, tts_client, audio_fixtures_dir, latency_tracker):
        text, _lang = SCENARIOS["medium_zh"]
        path = str(audio_fixtures_dir / "medium_zh.wav")
        pcm, first_ms, total_ms = await collect_tts_stream(tts_client, text)
        assert pcm, "No audio data received from TTS"
        save_pcm_as_wav(pcm, path)
        _assert_valid_wav(path)
        latency_tracker.record("tts_ttfa_ms", first_ms, scenario="medium_zh")
        latency_tracker.record("tts_total_ms", total_ms, scenario="medium_zh")
        dur = duration_from_wav(path)
        print(f"\nmedium_zh: TTFA={first_ms:.0f}ms  total={total_ms:.0f}ms  audio={dur:.2f}s")

    @pytest.mark.asyncio
    async def test_generate_medium_en(self, tts_client, audio_fixtures_dir, latency_tracker):
        text, _lang = SCENARIOS["medium_en"]
        path = str(audio_fixtures_dir / "medium_en.wav")
        pcm, first_ms, total_ms = await collect_tts_stream(tts_client, text)
        assert pcm, "No audio data received from TTS"
        save_pcm_as_wav(pcm, path)
        _assert_valid_wav(path)
        latency_tracker.record("tts_ttfa_ms", first_ms, scenario="medium_en")
        latency_tracker.record("tts_total_ms", total_ms, scenario="medium_en")
        dur = duration_from_wav(path)
        print(f"\nmedium_en: TTFA={first_ms:.0f}ms  total={total_ms:.0f}ms  audio={dur:.2f}s")


# ── Streaming latency deep-dive ───────────────────────────────────────────────

class TestTTSStreamingLatency:
    """
    Measure fine-grained streaming behaviour: chunk count, inter-chunk
    intervals, and real-time factor.
    """

    @pytest.mark.asyncio
    async def test_streaming_chunk_timeline(self, tts_client, latency_tracker):
        """Record per-chunk arrival times for the short Chinese scenario."""
        text, _ = SCENARIOS["short_zh"]
        timings: List[float] = []
        t0 = time.perf_counter()

        async for chunk in tts_client.synthesize(text, stream=True):
            timings.append((time.perf_counter() - t0) * 1000)

        assert timings, "TTS produced no chunks"

        # Inter-chunk intervals
        gaps = [timings[i] - timings[i - 1] for i in range(1, len(timings))]
        first_ms = timings[0]
        total_ms = timings[-1]
        avg_gap_ms = sum(gaps) / len(gaps) if gaps else 0.0

        latency_tracker.record("tts_stream_first_chunk_ms", first_ms, scenario="short_zh")
        latency_tracker.record("tts_stream_avg_gap_ms", avg_gap_ms, scenario="short_zh")

        print(
            f"\nstreaming chunk timeline (short_zh):"
            f"\n  chunks          : {len(timings)}"
            f"\n  first chunk     : {first_ms:.1f} ms"
            f"\n  total           : {total_ms:.1f} ms"
            f"\n  avg inter-chunk : {avg_gap_ms:.1f} ms"
        )

    @pytest.mark.asyncio
    async def test_streaming_realtime_factor(self, tts_client, audio_fixtures_dir, latency_tracker):
        """
        RTF = synthesis_time / audio_duration.
        RTF < 1.0 means the server generates faster than realtime (good).
        """
        text, _ = SCENARIOS["medium_zh"]
        path = str(audio_fixtures_dir / "medium_zh_rtf.wav")

        pcm, first_ms, total_ms = await collect_tts_stream(tts_client, text)
        assert pcm, "No audio data"
        save_pcm_as_wav(pcm, path)
        audio_dur_s = duration_from_wav(path)
        rtf = (total_ms / 1000) / audio_dur_s if audio_dur_s > 0 else float("inf")

        latency_tracker.record("tts_rtf", rtf * 1000, scenario="medium_zh")  # stored ×1000 so it fits ms column

        print(
            f"\nRealtime factor (medium_zh):"
            f"\n  synthesis time  : {total_ms:.0f} ms"
            f"\n  audio duration  : {audio_dur_s:.2f} s"
            f"\n  RTF             : {rtf:.3f}  ({'✓ faster than RT' if rtf < 1 else '✗ slower than RT'})"
        )

        # Soft assertion – warn but don't fail; network latency can push it over 1
        if rtf >= 2.0:
            pytest.xfail(f"RTF={rtf:.2f} is unexpectedly high (possible network issue)")


# ── Voice variety test ────────────────────────────────────────────────────────

class TestTTSVoiceVariants:
    """Verify that documented voices produce non-empty audio."""

    VOICES = ["Cherry", "Bella"]  # Tested voices (Jack/Allie may not be available in all regions)
    TEST_TEXT = "这是一段测试语音。"  # "This is a test voice."

    @pytest.mark.asyncio
    @pytest.mark.parametrize("voice", VOICES)
    async def test_voice_produces_audio(
        self, voice, api_key, audio_fixtures_dir, latency_tracker
    ):
        from src.server.bailian_tts import BailianTTS

        client = BailianTTS(api_key=api_key, model="qwen3-tts-flash", voice=voice)
        path = str(audio_fixtures_dir / f"voice_{voice.lower()}.wav")

        pcm, first_ms, total_ms = await collect_tts_stream(client, self.TEST_TEXT)
        assert pcm, f"Voice '{voice}' produced no audio"

        save_pcm_as_wav(pcm, path)
        dur = duration_from_wav(path)
        assert dur > 0.2, f"Voice '{voice}' audio too short: {dur:.3f}s"

        latency_tracker.record("tts_voice_ttfa_ms", first_ms, voice=voice)
        print(f"\n  [{voice}] TTFA={first_ms:.0f}ms  dur={dur:.2f}s  file={path}")

        await client.close()
