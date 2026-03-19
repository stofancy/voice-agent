"""
测试 dashscope tts_v2 SpeechSynthesizer 流式文本输入能力。

测试目标：
1. qwen3-tts-flash 是否支持 tts_v2 WebSocket 双工接口
2. 流式输入的首音频延迟 (TTFA)
3. 对比：一次性输入 vs 逐 token 流式输入

用法：
    export ALI_BAILIAN_API_KEY=sk-xxx
    python tests/test_tts_v2_streaming.py
"""

import os
import sys
import time
import threading

# dashscope tts_v2
from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat, ResultCallback


API_KEY = os.environ.get("ALI_BAILIAN_API_KEY")
if not API_KEY:
    print("❌ 请设置 ALI_BAILIAN_API_KEY 环境变量")
    sys.exit(1)

# 设置 dashscope api key
import dashscope
dashscope.api_key = API_KEY

TEST_TEXT = "你好，欢迎来到旅行助手。今天天气不错，适合出门走走。"
TEST_MODELS = [
    "cosyvoice-v2",
]
# CosyVoice 可用音色: longxiaochun, longxiaoxia, longlaotie, longshu, longjielidou, ...
# 参考: https://help.aliyun.com/zh/model-studio/cosyvoice-voice-list
TEST_VOICES = ["longxiaochun", "longxiaoxia"]


class TimingCallback(ResultCallback):
    """记录时间戳的回调"""

    def __init__(self, label: str):
        self.label = label
        self.first_audio_time = None
        self.start_time = None
        self.total_bytes = 0
        self.chunk_count = 0
        self.complete_time = None
        self.error_msg = None

    def on_open(self):
        print(f"  [{self.label}] WebSocket 已连接")

    def on_data(self, data: bytes):
        if self.first_audio_time is None:
            self.first_audio_time = time.perf_counter()
            ttfa = (self.first_audio_time - self.start_time) * 1000
            print(f"  [{self.label}] 🔊 首音频! TTFA={ttfa:.0f}ms")
        self.total_bytes += len(data)
        self.chunk_count += 1

    def on_complete(self):
        self.complete_time = time.perf_counter()
        total = (self.complete_time - self.start_time) * 1000
        print(f"  [{self.label}] ✅ 完成: {self.chunk_count} 块, {self.total_bytes} bytes, 总耗时 {total:.0f}ms")

    def on_error(self, message):
        self.error_msg = str(message)
        print(f"  [{self.label}] ❌ 错误: {message}")

    def on_close(self):
        pass


def test_one_shot(model: str, voice: str, text: str):
    """测试一次性输入（call）"""
    print(f"\n{'='*60}")
    print(f"📋 一次性输入测试: model={model}, voice={voice}")
    print(f"   文本: {text[:40]}...")

    cb = TimingCallback("one-shot")
    try:
        synth = SpeechSynthesizer(
            model=model,
            voice=voice,
            format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            callback=cb,
        )
        cb.start_time = time.perf_counter()
        synth.call(text)

        if cb.first_audio_time:
            ttfa = (cb.first_audio_time - cb.start_time) * 1000
            total = (cb.complete_time - cb.start_time) * 1000 if cb.complete_time else 0
            return {"ttfa_ms": ttfa, "total_ms": total, "bytes": cb.total_bytes, "error": None}
        else:
            return {"ttfa_ms": None, "total_ms": None, "bytes": 0, "error": cb.error_msg or "无音频输出"}
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return {"ttfa_ms": None, "total_ms": None, "bytes": 0, "error": str(e)}


def test_streaming(model: str, voice: str, text: str):
    """测试流式文本输入（streaming_call）"""
    print(f"\n{'='*60}")
    print(f"📋 流式输入测试: model={model}, voice={voice}")
    print(f"   文本: {text[:40]}...")

    cb = TimingCallback("stream")
    try:
        synth = SpeechSynthesizer(
            model=model,
            voice=voice,
            format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            callback=cb,
        )
        cb.start_time = time.perf_counter()

        # 模拟 LLM 逐 token 输出：每个字符间隔 50ms
        for i, char in enumerate(text):
            synth.streaming_call(char)
            if i == 0:
                print(f"  [{cb.label}] 发送首个 token: '{char}'")
            time.sleep(0.05)  # 模拟 LLM token 间隔

        print(f"  [{cb.label}] 所有 token 已发送, 调用 streaming_complete...")
        synth.streaming_complete()

        if cb.first_audio_time:
            ttfa = (cb.first_audio_time - cb.start_time) * 1000
            total = (cb.complete_time - cb.start_time) * 1000 if cb.complete_time else 0
            return {"ttfa_ms": ttfa, "total_ms": total, "bytes": cb.total_bytes, "error": None}
        else:
            return {"ttfa_ms": None, "total_ms": None, "bytes": 0, "error": cb.error_msg or "无音频输出"}
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return {"ttfa_ms": None, "total_ms": None, "bytes": 0, "error": str(e)}


def main():
    print("🧪 DashScope tts_v2 流式文本输入测试")
    print(f"   API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print(f"   测试文本: {TEST_TEXT}")
    print(f"   测试模型: {TEST_MODELS}")

    results = {}

    for model in TEST_MODELS:
        for voice in TEST_VOICES:
            print(f"\n\n{'#'*60}")
            print(f"# 模型: {model}, 音色: {voice}")
            print(f"{'#'*60}")

            # 一次性输入
            r1 = test_one_shot(model, voice, TEST_TEXT)
            results[f"{model}/{voice}/one-shot"] = r1

            time.sleep(1)

            # 流式输入
            r2 = test_streaming(model, voice, TEST_TEXT)
            results[f"{model}/{voice}/stream"] = r2

            time.sleep(1)

    # 汇总
    print(f"\n\n{'='*60}")
    print("📊 测试结果汇总")
    print(f"{'='*60}")
    print(f"{'测试':<30} {'TTFA(ms)':<12} {'总耗时(ms)':<12} {'音频(bytes)':<12} {'状态'}")
    print("-" * 80)
    for key, r in results.items():
        ttfa = f"{r['ttfa_ms']:.0f}" if r['ttfa_ms'] else "N/A"
        total = f"{r['total_ms']:.0f}" if r['total_ms'] else "N/A"
        byt = f"{r['bytes']}" if r['bytes'] else "0"
        status = "✅" if not r['error'] else f"❌ {r['error'][:30]}"
        print(f"{key:<30} {ttfa:<12} {total:<12} {byt:<12} {status}")


if __name__ == "__main__":
    main()
