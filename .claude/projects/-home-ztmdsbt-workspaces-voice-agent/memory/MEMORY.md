# Voice Agent 项目记忆

## 项目概述

实时语音对话后端服务，支持 STT → LLM → TTS 全流程流式处理。

## 关键架构

- **WebSocket 入口**: `src/server/main.py` - 消息循环、状态机、取消机制
- **语音对话编排**: `src/server/voice_turn.py` - STT + StreamingSynthesis
- **LLM+TTS 并行流**: `src/server/streaming_synthesis.py` - feed/consume 双循环
- **消息路由**: `src/server/message_router.py` - handler 模式解耦

## 开发原则

1. **增量提交**: 每完成一个小改动就立即提交
2. **Feature Branch**: 永远不在 main 分支直接提交
3. **单一职责**: 每个模块职责清晰
4. **开闭原则**: 对扩展开放，对修改关闭

## 重要文件

| 文件 | 用途 |
|------|------|
| `src/server/main.py` | WebSocket 端点，消息循环 |
| `src/server/streaming_synthesis.py` | LLM+TTS 并行流编排 |
| `src/server/voice_turn.py` | 完整语音对话流程 |
| `src/server/message_router.py` | 消息处理函数 |
| `src/server/connection.py` | 状态机 + WebSocket 封装 |
| `src/server/turn_context.py` | 对话取消信号 |

## 配置要点

- `OPENCLAW_TTS_PROVIDER=bailian_realtime` - 实时 TTS
- `OPENCLAW_TTS_TIME_BUFFER_SECONDS=0.5` - 低延迟缓冲
- `OPENCLAW_SUBTITLE_STREAMING=true` - 实时字幕

## 2026-03-22 重构完成

完成 main.py 重构：
- 提取 VoiceTurn、StreamingSynthesis、TurnContext
- 提取 message_router.py
- 修复 WebSocket double-close 错误
- 使用类型化消息 WSMessage

## Bug 修复记录

- `bailian_tts.py`: `start_time` → `first_chunk_time` (f620272)
