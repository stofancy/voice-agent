# E2E 延迟基准测试

## 当前基准（2026-03-19）

**架构**：TTS/STT/LLM 子模块化（ABC + Factory）
**测试脚本**：`tests/e2e/test_e2e_latency.py --rounds 3`
**测试音频**：`tests/e2e/fixtures/audio/short_zh.wav`（"你好，今天天气怎么样？"）

### 配置

| 组件 | 模型 | 接口 |
|------|------|------|
| STT | qwen3-asr-flash | HTTP (DashScope) |
| LLM | openclaw:main via Gateway | OpenAI 兼容 |
| TTS | qwen3-tts-flash-realtime | WebSocket 双工 (server_commit) |
| TTS 音色 | Maia | — |

### 结果

| 指标 | Avg | Min | P50 | P95 | Max | 单位 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| ① STT | 571 | 448 | 493 | 773 | 773 | ms |
| ② LLM TTFT | 1574 | 1431 | 1477 | 1813 | 1813 | ms |
| ③ LLM gen | 11 | 1 | 10 | 21 | 21 | ms |
| ④ TTS TTFA | 736 | 685 | 743 | 780 | 780 | ms |
| ⚡ E2E 首音频 | 2892 | 2624 | 2771 | 3280 | 3280 | ms |
| 📊 总轮次 | 3958 | 3803 | 3816 | 4254 | 4254 | ms |

### 延迟分布

```
STT (571ms, 20%) → LLM TTFT (1574ms, 54%) → TTS TTFA (736ms, 26%)
                          ↑ 主要瓶颈
```

---

## 历史基准

### 2026-03-18 — 旧架构（qwen3-tts-flash HTTP SSE）

| 指标 | Avg | P50 | 单位 |
|------|:---:|:---:|:---:|
| STT | 505 | 477 | ms |
| LLM TTFT | 1505 | 1403 | ms |
| LLM gen | 595 | 617 | ms |
| TTS TTFA | **6313** | **6003** | ms |
| ⚡ E2E | **8918** | **8809** | ms |

### 改进对比

| 指标 | 旧 → 新 | 提升 |
|------|---------|------|
| TTS TTFA | 6313ms → 736ms | **快 8.6 倍** |
| E2E 首音频 | 8918ms → 2892ms | **快 3.1 倍** |

**根因**：TTS 从 HTTP SSE（等全文再合成）切换到 WebSocket 双工（流式文本输入，server_commit 模式）。
