# Streaming Requirements Checklist: Self-Managed Agent Layer

**Purpose**: Validate streaming and non-blocking requirements quality
**Created**: 2026-03-25
**Updated**: 2026-03-27
**Feature**: [link](../spec.md)

## Streaming Completeness

- [x] CHK101 - Are all streaming events defined with payloads? [Completeness, Spec §FR-003] ✅ contracts/agent-interface.md
- [x] CHK102 - Is the relationship between streaming events and TTS audio flow specified? [Gap] ✅ via StreamController integration
- [x] CHK103 - Are buffer management requirements for streaming defined? [Gap] ✅ FR-009 event queue max depth = 100
- [x] CHK104 - Is backpressure handling during tool execution specified? [Gap] ✅ FR-009 + data-model.md

## Latency Requirements

- [x] CHK105 - Is 200ms gap requirement achievable with LangChain? [Feasibility] ✅ Assumptions: 50-100ms overhead
- [ ] CHK106 - Are STT-to-TTS end-to-end latency requirements specified? [Gap] ❌ not addressed
- [x] CHK107 - Is the measurement methodology for "gap in stream output" defined? [Measurability] ✅ SC-001 measurement
- [x] CHK108 - Are timeout values for tool execution specified? [Completeness] ✅ FR-007a 30s default

## Non-Blocking Requirements

- [x] CHK109 - Is "non-blocking" defined with specific technical criteria? [Clarity] ✅ via event queue + async
- [ ] CHK110 - Are thread/async model requirements for tool execution specified? [Gap] ❌ async assumed
- [x] CHK111 - Is the interaction between LLM streaming and tool streaming defined? [Gap] ✅ via StreamController
- [x] CHK112 - Are concurrent tool call scenarios addressed? [Coverage] ✅ sequential ReAct loop (known limitation)

## TTS Continuity

- [x] CHK113 - Is the "no silence >500ms" requirement achievable? [Feasibility] ✅ progress every 500ms
- [x] CHK114 - Are fallback TTS messages for tool execution specified? [Completeness] ✅ FR-007b/c
- [ ] CHK115 - Is TTS audio quality during streaming addressed? [Gap] ❌ out of scope
- [ ] CHK116 - Are audio buffer size requirements defined? [Gap] ❌ TTS module负责

## Progress Communication

- [ ] CHK117 - Are the exact progress messages for each tool type defined? [Gap] ❌ generic progress only, Phase 5
- [x] CHK118 - Is the timing/frequency of progress updates specified? [Gap] ✅ FR-010: every 500ms
- [x] CHK119 - Are user notification requirements for long-running tools defined? [Gap] ✅ timeout fallback
- [x] CHK120 - Is the balance between progress updates and TTS quality specified? [Gap] ✅ 500ms is balance

## Error Handling During Streaming

- [x] CHK121 - Is stream recovery after tool failure specified? [Coverage] ✅ FR-007c
- [ ] CHK122 - Are partial result handling requirements defined? [Gap] ❌ not addressed
- [x] CHK123 - Is the behavior when tool times out during streaming specified? [Edge Case] ✅ FR-007b + US1 scenario 4
- [x] CHK124 - Are retry requirements for failed tool calls during streaming defined? [Gap] ✅ Assumptions: no auto-retry

## Notes

**Updated 2026-03-27**: 补全了 streaming 相关的 spec 缺口

Remaining gaps:
- ❌ CHK106: STT-to-TTS 端到端延迟
- ❌ CHK110: async 模型文档
- ❌ CHK115/CHK116: TTS audio quality/buffer (TTS module负责)
- ❌ CHK117: 具体工具的进度消息 (Phase 5 query_tool)
- ❌ CHK122: partial result handling
