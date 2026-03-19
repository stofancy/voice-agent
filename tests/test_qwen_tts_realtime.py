"""
测试 QwenTtsRealtime 流式文本输入 (server_commit 模式)

测试:
1. qwen3-tts-flash-realtime TTFA
2. qwen3-tts-instruct-flash-realtime TTFA (带 instructions)
3. 流式逐 token 输入 vs 批量输入

用法:
    source .env && export ALI_BAILIAN_API_KEY && python3 tests/test_qwen_tts_realtime.py
"""

import os
import sys
import time
import threading
import base64

import dashscope
from dashscope.audio.qwen_tts_realtime import QwenTtsRealtime, QwenTtsRealtimeCallback, AudioFormat

API_KEY = os.environ.get("ALI_BAILIAN_API_KEY")
if not API_KEY:
    print("❌ 请设置 ALI_BAILIAN_API_KEY")
    sys.exit(1)
dashscope.api_key = API_KEY

TEXT = "你好，欢迎来到旅行助手。今天天气不错，适合出门走走。"
WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"


class TimingCallback(QwenTtsRealtimeCallback):
    def __init__(self, label):
        self.label = label
        self.t0 = None
        self.first_audio_time = None
        self.total_bytes = 0
        self.chunk_count = 0
        self.complete_event = threading.Event()
        self.error_msg = None

    def on_open(self):
        pass

    def on_close(self, code, msg):
        pass

    def on_event(self, response):
        try:
            etype = response.get("type", "")
            if etype == "session.created":
                pass
            elif etype == "response.audio.delta":
                audio_bytes = base64.b64decode(response["delta"])
                if self.first_audio_time is None:
                    self.first_audio_time = time.perf_counter()
                    ttfa = (self.first_audio_time - self.t0) * 1000
                    print(f"  [{self.label}] 🔊 首音频! TTFA={ttfa:.0f}ms")
                self.total_bytes += len(audio_bytes)
                self.chunk_count += 1
            elif etype == "response.done":
                t = (time.perf_counter() - self.t0) * 1000
                print(f"  [{self.label}] ✅ response.done: {self.chunk_count} 块, {self.total_bytes} bytes, {t:.0f}ms")
            elif etype == "session.finished":
                self.complete_event.set()
            elif etype == "error":
                self.error_msg = str(response.get("error", {}))
                print(f"  [{self.label}] ❌ Error: {self.error_msg}")
                self.complete_event.set()
        except Exception as e:
            print(f"  [{self.label}] ❌ Exception in callback: {e}")
            self.complete_event.set()

    def wait(self, timeout=30):
        self.complete_event.wait(timeout=timeout)


def test_server_commit_batch(model, voice, text, instructions=None):
    """server_commit 模式 - 批量发送文本"""
    label = f"{model.split('-realtime')[0]}/batch"
    print(f"\n{'='*60}")
    print(f"📋 server_commit 批量: model={model}, voice={voice}")
    if instructions:
        print(f"   instructions: {instructions[:40]}...")

    cb = TimingCallback(label)
    tts = QwenTtsRealtime(model=model, callback=cb, url=WS_URL)
    tts.connect()

    kwargs = dict(
        voice=voice,
        response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
        mode="server_commit",
    )
    if instructions:
        kwargs["instructions"] = instructions
        kwargs["optimize_instructions"] = True
    tts.update_session(**kwargs)

    cb.t0 = time.perf_counter()

    # 一次性发送全部文本
    tts.append_text(text)
    time.sleep(0.5)
    tts.finish()
    cb.wait()

    ttfa = (cb.first_audio_time - cb.t0) * 1000 if cb.first_audio_time else None
    return {"label": label, "ttfa_ms": ttfa, "bytes": cb.total_bytes, "error": cb.error_msg}


def test_server_commit_streaming(model, voice, text, instructions=None):
    """server_commit 模式 - 逐字符流式发送 (模拟 LLM)"""
    label = f"{model.split('-realtime')[0]}/stream"
    print(f"\n{'='*60}")
    print(f"📋 server_commit 流式: model={model}, voice={voice}")

    cb = TimingCallback(label)
    tts = QwenTtsRealtime(model=model, callback=cb, url=WS_URL)
    tts.connect()

    kwargs = dict(
        voice=voice,
        response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
        mode="server_commit",
    )
    if instructions:
        kwargs["instructions"] = instructions
        kwargs["optimize_instructions"] = True
    tts.update_session(**kwargs)

    cb.t0 = time.perf_counter()

    # 逐字符发送, 50ms 间隔模拟 LLM
    for ch in text:
        tts.append_text(ch)
        time.sleep(0.05)

    time.sleep(0.3)
    tts.finish()
    cb.wait()

    ttfa = (cb.first_audio_time - cb.t0) * 1000 if cb.first_audio_time else None
    return {"label": label, "ttfa_ms": ttfa, "bytes": cb.total_bytes, "error": cb.error_msg}


def main():
    print("🧪 QwenTtsRealtime 流式测试")
    print(f"   文本: {TEXT}")
    results = []

    # Test 1: qwen3-tts-flash-realtime 批量
    results.append(test_server_commit_batch("qwen3-tts-flash-realtime", "Cherry", TEXT))
    time.sleep(1)

    # Test 2: qwen3-tts-flash-realtime 流式
    results.append(test_server_commit_streaming("qwen3-tts-flash-realtime", "Cherry", TEXT))
    time.sleep(1)

    # Test 3: qwen3-tts-instruct-flash-realtime 批量 (带 instructions)
    instr = "年轻女性，音调偏高，声音清脆甜美，语速中等略快，语气温柔治愈又不失活力。"
    results.append(test_server_commit_batch("qwen3-tts-instruct-flash-realtime", "Maia", TEXT, instructions=instr))
    time.sleep(1)

    # Test 4: qwen3-tts-instruct-flash-realtime 流式 (带 instructions)
    results.append(test_server_commit_streaming("qwen3-tts-instruct-flash-realtime", "Maia", TEXT, instructions=instr))

    # 汇总
    print(f"\n\n{'='*60}")
    print("📊 测试结果汇总")
    print(f"{'='*60}")
    print(f"{'测试':<45} {'TTFA(ms)':<10} {'音频(bytes)':<12} {'状态'}")
    print("-" * 80)
    for r in results:
        ttfa = f"{r['ttfa_ms']:.0f}" if r['ttfa_ms'] else "N/A"
        status = "✅" if not r['error'] else f"❌ {r['error'][:30]}"
        print(f"{r['label']:<45} {ttfa:<10} {r['bytes']:<12} {status}")


if __name__ == "__main__":
    main()
