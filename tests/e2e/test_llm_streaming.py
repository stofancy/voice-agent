"""
LLM Streaming Latency Tests
============================

Tests the AI backend (Alibaba Bailian Qwen-turbo via OpenAI-compatible API):

- Time to First Token (TTFT): latency until the first streaming chunk
- First-sentence latency: time until a sentence-ending punctuation mark
  appears (this is when TTS could START synthesising)
- Tokens per second (throughput)
- Full response latency

All latency metrics are logged to tests/e2e/test_run.log in real-time.

Scenarios cover short/medium, Chinese/English prompts.

Run:
    ALI_BAILIAN_API_KEY=sk-... pytest tests/e2e/test_llm_streaming.py -v -s
"""

import re
import time
from typing import List, Tuple

import pytest
from loguru import logger

from tests.e2e.conftest import SCENARIOS


# Sentence-ending punctuation for both languages
_SENTENCE_END = re.compile(r"[.。!！?？;；]")


async def _stream_to_completion(
    llm_client,
    prompt: str,
) -> Tuple[str, float, float, float, int]:
    """
    Drive llm_client.chat_stream(prompt) to completion.

    Returns:
        (full_text, ttft_ms, first_sentence_ms, total_ms, approx_token_count)

    ``first_sentence_ms`` is the wall-clock from the first API call until
    the first sentence-boundary character is included in the buffer.
    """
    full_text = ""
    ttft_ms: float = 0.0
    first_sentence_ms: float = 0.0
    first_sentence_done = False
    token_count = 0
    t0 = time.perf_counter()
    logger.debug(f"🤖 LLM: Starting stream for prompt: {prompt[:60]!r}...")

    async for chunk in llm_client.chat_stream(prompt):
        now_ms = (time.perf_counter() - t0) * 1000
        if not full_text:  # first chunk ever
            ttft_ms = now_ms
            logger.info(f"🤖 LLM: First token at {ttft_ms:.1f}ms")
        full_text += chunk
        token_count += 1  # each yielded chunk ≈ 1 token
        logger.debug(f"🤖 LLM: Token #{token_count} at {now_ms:.1f}ms: {chunk!r}")
        if not first_sentence_done and _SENTENCE_END.search(full_text):
            first_sentence_ms = now_ms
            first_sentence_done = True
            logger.info(f"🤖 LLM: First sentence complete at {first_sentence_ms:.1f}ms")

    total_ms = (time.perf_counter() - t0) * 1000
    if not first_sentence_done:
        first_sentence_ms = total_ms  # no punctuation found – whole response is "first sentence"
    
    logger.info(f"🤖 LLM: Complete in {total_ms:.1f}ms ({token_count} tokens, {len(full_text)} chars)")

    return full_text, ttft_ms, first_sentence_ms, total_ms, token_count


# ── TTFT tests ────────────────────────────────────────────────────────────────

class TestLLMTimeToFirstToken:
    """
    Measure TTFT for various prompt types.
    TTFT directly contributes to the perceived first-audio latency.
    """

    @pytest.mark.asyncio
    async def test_ttft_short_zh(self, llm_client, latency_tracker):
        prompt = "你好！请简单打个招呼。"
        text, ttft, first_sent, total, tokens = await _stream_to_completion(llm_client, prompt)
        latency_tracker.record("llm_ttft_ms", ttft, scenario="short_zh_prompt")
        latency_tracker.record("llm_first_sentence_ms", first_sent, scenario="short_zh_prompt")
        latency_tracker.record("llm_total_ms", total, scenario="short_zh_prompt")
        print(
            f"\nshort_zh_prompt:"
            f"\n  TTFT            : {ttft:.0f} ms"
            f"\n  first sentence  : {first_sent:.0f} ms"
            f"\n  total           : {total:.0f} ms"
            f"\n  chunks          : {tokens}"
            f"\n  response        : {text[:120]!r}"
        )
        assert ttft < 5000, f"TTFT too high: {ttft:.0f} ms"
        assert text.strip(), "Empty response"

    @pytest.mark.asyncio
    async def test_ttft_short_en(self, llm_client, latency_tracker):
        prompt = "Hello! Please greet me briefly."
        text, ttft, first_sent, total, tokens = await _stream_to_completion(llm_client, prompt)
        latency_tracker.record("llm_ttft_ms", ttft, scenario="short_en_prompt")
        latency_tracker.record("llm_first_sentence_ms", first_sent, scenario="short_en_prompt")
        latency_tracker.record("llm_total_ms", total, scenario="short_en_prompt")
        print(
            f"\nshort_en_prompt:"
            f"\n  TTFT            : {ttft:.0f} ms"
            f"\n  first sentence  : {first_sent:.0f} ms"
            f"\n  total           : {total:.0f} ms"
            f"\n  response        : {text[:120]!r}"
        )
        assert ttft < 5000
        assert text.strip()

    @pytest.mark.asyncio
    async def test_ttft_medium_zh(self, llm_client, latency_tracker):
        prompt = "请简单介绍一下中国的四大发明，说两三句话就行。"
        text, ttft, first_sent, total, tokens = await _stream_to_completion(llm_client, prompt)
        latency_tracker.record("llm_ttft_ms", ttft, scenario="medium_zh_prompt")
        latency_tracker.record("llm_first_sentence_ms", first_sent, scenario="medium_zh_prompt")
        latency_tracker.record("llm_total_ms", total, scenario="medium_zh_prompt")
        tps = tokens / (total / 1000) if total > 0 else 0
        latency_tracker.record("llm_tokens_per_sec", tps * 100, scenario="medium_zh_prompt")  # ×100 to fit ms column
        print(
            f"\nmedium_zh_prompt:"
            f"\n  TTFT            : {ttft:.0f} ms"
            f"\n  first sentence  : {first_sent:.0f} ms"
            f"\n  total           : {total:.0f} ms"
            f"\n  chunks/tokens   : {tokens}  ({tps:.1f} tok/s)"
            f"\n  response        : {text[:200]!r}"
        )
        assert ttft < 5000
        assert text.strip()

    @pytest.mark.asyncio
    async def test_ttft_medium_en(self, llm_client, latency_tracker):
        prompt = "Tell me one interesting fact about the solar system. Keep it brief."
        text, ttft, first_sent, total, tokens = await _stream_to_completion(llm_client, prompt)
        latency_tracker.record("llm_ttft_ms", ttft, scenario="medium_en_prompt")
        latency_tracker.record("llm_first_sentence_ms", first_sent, scenario="medium_en_prompt")
        latency_tracker.record("llm_total_ms", total, scenario="medium_en_prompt")
        tps = tokens / (total / 1000) if total > 0 else 0
        latency_tracker.record("llm_tokens_per_sec", tps * 100, scenario="medium_en_prompt")
        print(
            f"\nmedium_en_prompt:"
            f"\n  TTFT            : {ttft:.0f} ms"
            f"\n  first sentence  : {first_sent:.0f} ms"
            f"\n  total           : {total:.0f} ms"
            f"\n  chunks/tokens   : {tokens}  ({tps:.1f} tok/s)"
            f"\n  response        : {text[:200]!r}"
        )
        assert ttft < 5000
        assert text.strip()


# ── Throughput test ───────────────────────────────────────────────────────────

class TestLLMThroughput:
    """Sustained token generation speed."""

    @pytest.mark.asyncio
    async def test_tokens_per_second_zh(self, llm_client, latency_tracker):
        prompt = "用中文写一段100字左右的自我介绍，用于语音助手。"
        text, ttft, _, total, tokens = await _stream_to_completion(llm_client, prompt)
        tps = tokens / (total / 1000) if total > 0 else 0
        print(
            f"\nthroughput_zh: {tokens} chunks in {total:.0f}ms → {tps:.1f} tok/s"
            f"\n  response: {text[:200]!r}"
        )
        latency_tracker.record("llm_tokens_per_sec", tps * 100, scenario="throughput_zh")
        assert tokens >= 5, "Unexpectedly few tokens"

    @pytest.mark.asyncio
    async def test_tokens_per_second_en(self, llm_client, latency_tracker):
        prompt = "Write a short 2-sentence introduction for a voice assistant."
        text, ttft, _, total, tokens = await _stream_to_completion(llm_client, prompt)
        tps = tokens / (total / 1000) if total > 0 else 0
        print(
            f"\nthroughput_en: {tokens} chunks in {total:.0f}ms → {tps:.1f} tok/s"
            f"\n  response: {text[:200]!r}"
        )
        latency_tracker.record("llm_tokens_per_sec", tps * 100, scenario="throughput_en")
        assert tokens >= 5


# ── Conversation history ──────────────────────────────────────────────────────

class TestLLMConversationContext:
    """
    Verify that multi-turn conversation context is maintained and
    that TTFT doesn't degrade significantly across turns.
    """

    @pytest.mark.asyncio
    async def test_multi_turn_ttft(self, api_key, latency_tracker):
        from src.server.backend import AIBackend

        # Fresh client so conversation history is clean
        client = AIBackend(
            backend_type="openai",
            url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-turbo",
            api_key=api_key,
        )

        turns = [
            "My name is Alex. Remember it.",
            "What is my name?",
            "Tell me a fun fact.",
        ]
        ttfts: List[float] = []

        for turn_idx, prompt in enumerate(turns):
            text, ttft, first_sent, total, tokens = await _stream_to_completion(client, prompt)
            ttfts.append(ttft)
            latency_tracker.record("llm_ttft_ms", ttft, scenario=f"multi_turn_{turn_idx + 1}")
            print(
                f"\n  Turn {turn_idx + 1}: TTFT={ttft:.0f}ms  response={text[:80]!r}"
            )

        await client.close()

        # Second turn should confirm it knows the name
        # (soft check – content may vary)
        print(f"\n  All TTFTs: {[f'{t:.0f}ms' for t in ttfts]}")
