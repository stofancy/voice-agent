# WebSocket Endpoint 测试用例文档

本文档定义了 `websocket_endpoint` 函数的所有测试用例，用于在重构过程中保护现有逻辑。

## 测试覆盖范围

### 1. 消息处理分支 (Message Handling)

| 用例ID | 用例名称 | 输入 | 预期输出 | 优先级 |
|--------|----------|------|----------|--------|
| MSG-001 | start_listening_开始录音 | `{"type": "start_listening"}` | 发送 `{"type": "listening_started"}`，清空 audio_buffer，设置状态为 LISTENING | P0 |
| MSG-002 | stop_listening_空缓冲区 | `{"type": "stop_listening"}`（无 audio） | 发送 `{"type": "listening_stopped"}`，不触发 STT | P0 |
| MSG-003 | stop_listening_有音频 | `{"type": "stop_listening"}`（有 audio） | 触发 run_turn，发送 transcript | P0 |
| MSG-004 | interrupt_中断 | `{"type": "interrupt"}` | 发送 `{"type": "interrupt_ack"}`，取消 response_task，发送 `{"type": "interrupt_complete"}` | P0 |
| MSG-005 | audio_录音中 | `{"type": "audio", "data": <base64>}`（状态=LISTENING） | 追加到 audio_buffer，调用 VAD.is_speech()，发送 `{"type": "vad_status"}` | P0 |
| MSG-006 | audio_非录音状态 | `{"type": "audio", "data": <base64>}`（状态≠LISTENING） | 忽略，不追加到 buffer | P0 |
| MSG-007 | ping_心跳 | `{"type": "ping"}` | 发送 `{"type": "pong"}` | P0 |
| MSG-008 | perf_report_性能报告 | `{"type": "perf_report", "metrics": {...}}` | 调用 `perf_logger.log_round()` | P1 |
| MSG-009 | unknown_未知消息 | `{"type": "unknown_type"}` | 忽略，不报错 | P2 |

### 2. run_turn 函数分支

| 用例ID | 用例名称 | 输入条件 | 预期行为 | 优先级 |
|--------|----------|----------|----------|--------|
| TURN-001 | 空转录本_早期返回 | STT 返回 `("", True)` | 发送 transcript，立即返回，发送 listening_stopped，不触发 TTS | P0 |
| TURN-002 | STT失败_早期返回 | STT 返回 `("text", False)` | 发送 transcript，立即返回，发送 listening_stopped，不触发 TTS | P0 |
| TURN-003 | 成功转录_进入LLM_TTS | STT 返回 `("Hello", True)` | 发送 transcript，触发 LLM+TTS 并行执行 | P0 |
| TURN-004 | STT异常 | STT 抛出异常 | 捕获异常，发送 fallback 消息 | P0 |

### 3. LLM+TTS 并行执行

| 用例ID | 用例名称 | 条件 | 预期行为 | 优先级 |
|--------|----------|------|----------|--------|
| PIPELINE-001 | 正常完成 | LLM 和 TTS 都正常 | 发送 tts_start, audio_chunk (多个), tts_end, response_complete | P0 |
| PIPELINE-002 | LLM异常 | chat_stream 抛出异常 | 捕获异常，发送 fallback，发送 tts_end(interrupted=True) | P0 |
| PIPELINE-003 | TTS异常 | TTS stream 迭代抛出异常 | 捕获异常，发送 fallback，发送 tts_end(interrupted=True) | P0 |
| PIPELINE-004 | WebSocket断开 | 并行执行中客户端断开 | 捕获 WebSocketDisconnect，清理资源 | P0 |
| PIPELINE-005 | 取消_CancelledError | cancel_response 取消任务 | 发送 tts_end(interrupted=True)，发送 listening_stopped | P0 |
| PIPELINE-006 | feed调用次数 | LLM yield 3个chunk | tts_stream.feed() 被调用 3 次 | P1 |
| PIPELINE-007 | subtitle发送 | SUBTITLE_STREAMING=true，LLM yield | 发送 subtitle_chunk 消息 | P1 |

### 4. 异常处理

| 用例ID | 用例名称 | 条件 | 预期行为 | 优先级 |
|--------|----------|------|----------|--------|
| EXC-001 | CancelledError_处理 | run_turn 中发生 CancelledError | 发送 tts_end(interrupted=True)，发送 listening_stopped，重新抛出 | P0 |
| EXC-002 | GenericException_处理 | run_turn 中发生 Exception | 发送 fallback 消息，发送 tts_end(interrupted=True) | P0 |
| EXC-003 | WebSocket发送失败 | 异常处理中 WebSocket 已断开 | 静默忽略，不抛出 | P0 |
| EXC-004 | 外部异常_清理 | outer handler 捕获 WebSocketDisconnect | 调用 cancel_response，关闭 WebSocket | P0 |

### 5. 状态机转换

| 用例ID | 用例名称 | 转换 | 预期行为 | 优先级 |
|--------|----------|------|----------|--------|
| STATE-001 | IDLE到LISTENING | start_listening | 状态变为 LISTENING | P0 |
| STATE-002 | LISTENING到PROCESSING | stop_listening with audio | 状态变为 PROCESSING | P0 |
| STATE-003 | PROCESSING到SPEAKING | tts.start() | 状态变为 SPEAKING | P0 |
| STATE-004 | SPEAKING到IDLE | send_listening_stopped_once() | 状态变为 IDLE | P0 |
| STATE-005 | 任意到IDLE_取消 | cancel_response 完成 | 状态变为 IDLE | P0 |
| STATE-006 | 非LISTENING状态收到stop | stop_listening（状态≠LISTENING） | 发送 listening_stopped，状态变为 IDLE | P0 |

### 6. cancel_response 函数

| 用例ID | 用例名称 | 条件 | 预期行为 | 优先级 |
|--------|----------|------|----------|--------|
| CANCEL-001 | task为None | response_task=None | 无操作，直接返回 | P0 |
| CANCEL-002 | task未完成 | response_task 正在运行 | 取消 task，等待完成 | P0 |
| CANCEL-003 | task已完成 | response_task 已完成 | 无操作，直接返回 | P0 |
| CANCEL-004 | send_interrupt_event_True | send_interrupt_event=True | 额外发送 interrupt_complete | P0 |

### 7. 性能日志

| 用例ID | 用例名称 | 条件 | 预期行为 | 优先级 |
|--------|----------|------|----------|--------|
| PERF-001 | perf_logger启用 | perf_logger.is_enabled()=True | perf_data 被填充并传递给 log_round | P1 |
| PERF-002 | perf_logger禁用 | perf_logger.is_enabled()=False | perf_data 保持为空，不调用 log_round | P1 |

---

## Mock 对象规范

### TTS Stream Mock
```python
class MockTTSStream:
    audio_chunks: list[bytes]  # 迭代时返回的音频块
    raise_exception: bool       # 是否抛出异常
    feed_called: bool          # feed() 是否被调用
    finish_called: bool        # finish() 是否被调用
    ensure_connected_called: bool  # _ensure_connected() 是否被调用
```

### WebSocket Mock
```python
class MockWebSocket:
    receive_texts: list[str]   # 依次返回的消息
    raise_disconnect: bool      # receive_text 是否抛出 WebSocketDisconnect
    raise_on_send: bool        # send_json 是否抛出 RuntimeError
    sent_messages: list[dict]  # 发送的消息列表
```

### Mock 返回值配置
| 对象 | 方法 | 配置 |
|------|------|------|
| stt | transcribe() | return (transcript, success) |
| tts | create_stream() | return MockTTSStream |
| backend | chat_stream() | yield text chunks 或 raise Exception |
| vad | is_speech() | return bool |
| perf_logger | is_enabled() | return bool |
| perf_logger | log_round() | no-op |

---

## 测试执行顺序

建议按优先级分组执行：
1. P0 核心路径测试（MSG-001 到 EXC-004, STATE-001 到 CANCEL-004）
2. P1 扩展测试（PIPELINE-006, PIPELINE-007, PERF-001, PERF-002, MSG-008）
3. P2 边界测试（MSG-009）

---

## 回归测试策略

重构后必须通过所有 P0 测试用例，确保：
1. 消息协议行为不变
2. 状态转换逻辑不变
3. 异常处理行为不变
4. 并行执行逻辑不变
