#!/usr/bin/env python3
"""
E2E Latency Test — Full WebSocket Pipeline
============================================

Measures real end-to-end latency through the WebSocket interface:

    User stops speaking (stop_listening)
    → STT transcription (transcript)
    → LLM first token (first subtitle_chunk)
    → LLM complete (last subtitle_chunk)
    → TTS first audio (first audio_chunk)
    → TTS complete (tts_end)

Total perceived latency = first audio_chunk - stop_listening

Usage:
    python tests/e2e/test_e2e_latency.py [--rounds 5] [--url ws://localhost:8765/ws] [--audio tests/e2e/fixtures/audio/short_zh.wav]

Requires: websockets, numpy
    pip install websockets numpy
"""

import argparse
import asyncio
import base64
import json
import statistics
import struct
import sys
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class LatencyResult:
    """Timestamps and computed latencies for one round."""
    round_num: int = 0

    # Raw timestamps (perf_counter)
    t_stop_listening: float = 0.0
    t_transcript: float = 0.0
    t_first_subtitle: float = 0.0
    t_last_subtitle: float = 0.0
    t_first_audio: float = 0.0
    t_tts_end: float = 0.0

    # Extracted data
    transcript_text: str = ""
    subtitle_text: str = ""
    audio_chunks_count: int = 0
    audio_bytes_total: int = 0

    @property
    def stt_ms(self) -> float:
        """① STT latency: stop_listening → transcript"""
        return (self.t_transcript - self.t_stop_listening) * 1000

    @property
    def llm_ttft_ms(self) -> float:
        """② LLM TTFT: transcript → first subtitle_chunk"""
        if self.t_first_subtitle == 0:
            return 0
        return (self.t_first_subtitle - self.t_transcript) * 1000

    @property
    def llm_generation_ms(self) -> float:
        """③ LLM generation: first subtitle → last subtitle"""
        if self.t_first_subtitle == 0 or self.t_last_subtitle == 0:
            return 0
        return (self.t_last_subtitle - self.t_first_subtitle) * 1000

    @property
    def tts_ttfa_ms(self) -> float:
        """④ TTS TTFA: last subtitle → first audio_chunk"""
        if self.t_first_audio == 0 or self.t_last_subtitle == 0:
            return 0
        return (self.t_first_audio - self.t_last_subtitle) * 1000

    @property
    def e2e_ms(self) -> float:
        """Total E2E: stop_listening → first audio_chunk"""
        if self.t_first_audio == 0:
            return 0
        return (self.t_first_audio - self.t_stop_listening) * 1000

    @property
    def total_ms(self) -> float:
        """Total round: stop_listening → tts_end"""
        if self.t_tts_end == 0:
            return 0
        return (self.t_tts_end - self.t_stop_listening) * 1000


def read_wav_as_float32_chunks(path: str, chunk_duration_ms: int = 250) -> List[bytes]:
    """
    Read a WAV file and return list of base64-encodable float32 PCM chunks.
    Simulates how the browser sends audio data. No numpy required.
    """
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())

    # Convert to float32 mono using struct (no numpy needed)
    if sampwidth == 2:
        n_samples = len(raw) // 2
        int16_samples = struct.unpack(f"<{n_samples}h", raw)
        float32_samples = [s / 32768.0 for s in int16_samples]
    elif sampwidth == 4:
        n_samples = len(raw) // 4
        int32_samples = struct.unpack(f"<{n_samples}i", raw)
        float32_samples = [s / 2147483648.0 for s in int32_samples]
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    # Take first channel if stereo
    if n_channels > 1:
        float32_samples = float32_samples[::n_channels]

    # Split into chunks and pack as float32 bytes
    chunk_samples = int(sr * chunk_duration_ms / 1000)
    chunks = []
    for i in range(0, len(float32_samples), chunk_samples):
        chunk = float32_samples[i:i + chunk_samples]
        chunk_bytes = struct.pack(f"<{len(chunk)}f", *chunk)
        chunks.append(base64.b64encode(chunk_bytes).decode())

    return chunks


async def run_one_round(
    ws_url: str,
    audio_chunks_b64: List[str],
    round_num: int,
    chunk_interval_ms: int = 250,
    timeout_s: float = 30.0,
) -> LatencyResult:
    """Run a single E2E latency test round via WebSocket."""
    import websockets

    result = LatencyResult(round_num=round_num)

    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        # Wait for connection to stabilize
        await asyncio.sleep(0.3)

        # 1. Send start_listening
        await ws.send(json.dumps({"type": "start_listening"}))

        # Wait for listening_started
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        assert msg["type"] == "listening_started", f"Expected listening_started, got {msg}"

        # 2. Stream audio chunks (simulating browser mic input)
        for chunk_b64 in audio_chunks_b64:
            await ws.send(json.dumps({"type": "audio", "data": chunk_b64}))
            await asyncio.sleep(chunk_interval_ms / 1000)

        # 3. Send stop_listening — this is T0
        await ws.send(json.dumps({"type": "stop_listening"}))
        result.t_stop_listening = time.perf_counter()

        # 4. Collect all response events until listening_stopped
        subtitle_parts = []
        done = False

        while not done:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout_s)
            except asyncio.TimeoutError:
                print(f"  ⚠️  Round {round_num}: timeout waiting for response")
                break

            now = time.perf_counter()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "transcript":
                result.t_transcript = now
                result.transcript_text = msg.get("text", "")

            elif msg_type == "subtitle_chunk":
                if result.t_first_subtitle == 0:
                    result.t_first_subtitle = now
                result.t_last_subtitle = now
                subtitle_parts.append(msg.get("text", ""))

            elif msg_type == "response_chunk":
                # Non-streaming fallback
                if result.t_first_subtitle == 0:
                    result.t_first_subtitle = now
                result.t_last_subtitle = now
                subtitle_parts.append(msg.get("text", ""))

            elif msg_type == "audio_chunk":
                if result.t_first_audio == 0:
                    result.t_first_audio = now
                result.audio_chunks_count += 1
                audio_data = msg.get("data", "")
                if audio_data:
                    result.audio_bytes_total += len(base64.b64decode(audio_data))

            elif msg_type == "tts_start":
                pass  # Noted but not tracked

            elif msg_type == "tts_end":
                result.t_tts_end = now

            elif msg_type == "response_complete":
                pass

            elif msg_type == "listening_stopped":
                done = True

            elif msg_type == "vad_status":
                pass  # Ignore VAD during playback

        result.subtitle_text = "".join(subtitle_parts)

    return result


def print_round_result(r: LatencyResult):
    """Print a single round's latency breakdown."""
    print(f"\n  Round {r.round_num}:")
    print(f"    STT:        {r.transcript_text[:60]!r}")
    print(f"    Response:   {r.subtitle_text[:60]!r}")
    print(f"    ┌─────────────────────────────────────────────┐")
    print(f"    │ ① STT latency      : {r.stt_ms:>8.0f} ms          │")
    print(f"    │ ② LLM TTFT         : {r.llm_ttft_ms:>8.0f} ms          │")
    print(f"    │ ③ LLM generation   : {r.llm_generation_ms:>8.0f} ms          │")
    print(f"    │ ④ TTS TTFA         : {r.tts_ttfa_ms:>8.0f} ms          │")
    print(f"    │─────────────────────────────────────────────│")
    print(f"    │ ⚡ E2E (to 1st audio): {r.e2e_ms:>7.0f} ms          │")
    print(f"    │ 📊 Total round      : {r.total_ms:>7.0f} ms          │")
    print(f"    │ 🔊 Audio chunks     : {r.audio_chunks_count:>7d}             │")
    print(f"    │ 📦 Audio bytes      : {r.audio_bytes_total:>7d}             │")
    print(f"    └─────────────────────────────────────────────┘")


def print_summary(results: List[LatencyResult]):
    """Print aggregate statistics across all rounds."""
    valid = [r for r in results if r.e2e_ms > 0]
    if not valid:
        print("\n  ❌ No valid results to summarize.")
        return

    def stats(values):
        if not values:
            return {"avg": 0, "min": 0, "max": 0, "p50": 0, "p95": 0}
        s = sorted(values)
        return {
            "avg": statistics.mean(s),
            "min": min(s),
            "max": max(s),
            "p50": s[len(s) // 2],
            "p95": s[int(len(s) * 0.95)] if len(s) >= 2 else s[-1],
        }

    metrics = {
        "① STT":         stats([r.stt_ms for r in valid]),
        "② LLM TTFT":    stats([r.llm_ttft_ms for r in valid]),
        "③ LLM gen":     stats([r.llm_generation_ms for r in valid]),
        "④ TTS TTFA":    stats([r.tts_ttfa_ms for r in valid]),
        "⚡ E2E":         stats([r.e2e_ms for r in valid]),
        "📊 Total":       stats([r.total_ms for r in valid]),
    }

    print(f"\n{'='*70}")
    print(f"  E2E LATENCY REPORT  ({len(valid)} rounds)")
    print(f"{'='*70}")
    print(f"  {'Metric':<16} {'Avg':>8} {'Min':>8} {'P50':>8} {'P95':>8} {'Max':>8}  (ms)")
    print(f"  {'─'*64}")
    for name, s in metrics.items():
        print(f"  {name:<16} {s['avg']:>8.0f} {s['min']:>8.0f} {s['p50']:>8.0f} {s['p95']:>8.0f} {s['max']:>8.0f}")
    print(f"{'='*70}")

    # Save JSON report
    report = {
        "rounds": len(valid),
        "metrics": {k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in metrics.items()},
        "raw": [
            {
                "round": r.round_num,
                "stt_ms": round(r.stt_ms, 1),
                "llm_ttft_ms": round(r.llm_ttft_ms, 1),
                "llm_gen_ms": round(r.llm_generation_ms, 1),
                "tts_ttfa_ms": round(r.tts_ttfa_ms, 1),
                "e2e_ms": round(r.e2e_ms, 1),
                "total_ms": round(r.total_ms, 1),
                "transcript": r.transcript_text[:100],
            }
            for r in valid
        ],
    }

    report_path = Path(__file__).parent / "e2e_latency_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n  📄 Report saved → {report_path}")


async def main():
    parser = argparse.ArgumentParser(description="E2E Latency Test for OpenClaw Voice")
    parser.add_argument("--rounds", type=int, default=5, help="Number of test rounds (default: 5)")
    parser.add_argument("--url", default="ws://localhost:8765/ws", help="WebSocket URL")
    parser.add_argument("--audio", default=None, help="WAV audio fixture path")
    parser.add_argument("--pause", type=float, default=2.0, help="Pause between rounds (seconds)")
    args = parser.parse_args()

    # Find audio fixture
    audio_path = args.audio
    if not audio_path:
        default_path = Path(__file__).parent / "fixtures" / "audio" / "short_zh.wav"
        if default_path.exists():
            audio_path = str(default_path)
        else:
            print(f"❌ No audio fixture found. Provide --audio path.")
            sys.exit(1)

    print(f"🎤 E2E Latency Test")
    print(f"   URL:    {args.url}")
    print(f"   Audio:  {audio_path}")
    print(f"   Rounds: {args.rounds}")

    # Pre-load audio chunks
    audio_chunks = read_wav_as_float32_chunks(audio_path)
    print(f"   Chunks: {len(audio_chunks)} (250ms each)")

    results: List[LatencyResult] = []

    for i in range(1, args.rounds + 1):
        print(f"\n{'─'*50}")
        print(f"  🔄 Round {i}/{args.rounds}")
        try:
            result = await run_one_round(args.url, audio_chunks, i)
            results.append(result)
            print_round_result(result)
        except Exception as e:
            print(f"  ❌ Round {i} failed: {e}")

        if i < args.rounds:
            await asyncio.sleep(args.pause)

    print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
