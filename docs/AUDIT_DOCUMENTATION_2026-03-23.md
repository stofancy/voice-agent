# OpenClaw Voice Agent — 文档审查与清理报告

**审查日期**: 2026-03-23
**审查范围**: 项目中所有 `.md` 文档文件（39 个）

---

## 1. 文档清单

### 1.1 根目录文档

| # | 文件 | 行数 | 最后更新 | 相关性 | 备注 |
|---|------|------|----------|--------|------|
| 1 | `README.md` | 211 | 2026-03-17 | **高** | 主 README，描述当前 Bailian 架构 |
| 2 | `README.bailian.md` | 199 | 2026-03-17 | **中** | Bailian Docker 部署指南 |
| 3 | `CLAUDE.md` | 127 | 2026-03-22 | **高** | Claude Code 项目指南，最近更新 |
| 4 | `CONFIG_REFERENCE.md` | 154 | 2026-03-20 | **高** | 配置参考文档 |
| 5 | `TODOS.md` | 260 | 2026-03-22 | **高** | 任务跟踪 |
| 6 | `HANDOVER.md` | 298 | 2026-03-17 | **中** | 项目交接文档 |
| 7 | `SKILL.md` | 113 | 2026-02-01 | **❌ 过时** | 严重过时，描述旧架构，待删除 |
| 8 | `COMPLETION_REPORT.md` | 252 | 2026-03-18 | **低** | 历史完成报告，待归档标记 |

### 1.2 docs/ 目录

| # | 文件 | 行数 | 最后更新 | 相关性 |
|---|------|------|----------|--------|
| 9 | `REFACTORING_PLAN_main_py.md` | 387 | 2026-03-22 | **高** |
| 10 | `test_cases/websocket_endpoint_test_cases.md` | 128 | 2026-03-22 | **高** |
| 11 | `TESTING_GUIDELINE.md` | 231 | 2026-03-17 | **高** |
| 12 | `E2E_BASELINE.md` | 57 | 2026-03-19 | **高** |
| 13 | `DESIGN_v2.md` | 397 | 2026-03-17 | **中** |
| 14 | `DEVELOPMENT_PLAN_v2.md` | 289 | 2026-03-17 | **中** |
| 15 | `V2_DISCOVERY_FRONTEND_BACKEND.md` | 55 | 2026-03-17 | **中** |
| 16 | `V2_EXECUTION_PLAN_FULL_SCOPE.md` | 90 | 2026-03-17 | **中** |
| 17 | `V2_DISCOVERY_DOCS_AUDIT.md` | 33 | 2026-03-17 | **中** |
| 18 | `DOCKER_MIGRATION_GUIDE.md` | 264 | 2026-03-18 | **中** |
| 19 | `models/tts_realtime.md` | 2638 | 2026-03-19 | **中** |
| 20 | `twitter-article.md` | 90 | 2026-03-17 | **低** |
| 21 | `SESSION_HANDOVER_2026-03-18.md` | 289 | 2026-03-18 | **低**（历史） |
| 22 | `DESIGN_v2_REVIEW.md` | 123 | 2026-03-17 | **低**（历史） |
| 23 | `DEVELOPMENT_PLAN_v2_REVIEW.md` | 148 | 2026-03-17 | **低**（历史） |

### 1.3 其他位置文档

| # | 文件 | 相关性 | 备注 |
|---|------|--------|------|
| 24 | `.github/copilot-instructions.md` | **中** | 需微调移除 Whisper 引用 |
| 25 | `.github/skills/openclaw-docs/SKILL.md` | **高** | OpenClaw 文档检索技能 |
| 26 | `.claude/skills/*.md`（6 个文件） | **高** | Claude 技能文档，最近更新 |
| 27 | `.claude/projects/.../MEMORY.md` | **高** | Claude 记忆文件 |
| 28 | `deploy/runpod/README.md` | **低**（过时） | 引用旧 Whisper 模型 |
| 29 | `tests/e2e/README.md` | **高** | E2E 测试文档 |
| 30 | `openclaw-gateway-config/README.md` | **中** | Gateway 配置指南 |

---

## 2. 过时引用追踪

### 2.1 Whisper / faster-whisper 引用

| 文件 | 行/位置 | 引用内容 |
|------|---------|----------|
| `SKILL.md` | 全文 | 主要架构基于 Whisper STT |
| `COMPLETION_REPORT.md` | 多处 | "分析原项目架构（Whisper STT + ElevenLabs TTS）" |
| `.github/copilot-instructions.md` | L43 | 架构图中有 `(Optional) Faster-Whisper` |
| `.github/copilot-instructions.md` | L94 | `OPENCLAW_STT_MODEL=qwen3-asr-flash # Bailian model (or 'whisper')` |
| `.github/copilot-instructions.md` | L168 | `pip install torch torchaudio  # For VAD, faster-whisper` |
| `.github/copilot-instructions.md` | L321 | 高延迟问题建议 "Large Whisper model" |
| `deploy/runpod/README.md` | L32+ | 假设 GPU 加速本地 Whisper 推理 |

### 2.2 ElevenLabs 引用

| 文件 | 引用内容 |
|------|----------|
| `SKILL.md` | 主要 TTS 架构基于 ElevenLabs |
| `COMPLETION_REPORT.md` | "原 ElevenLabs TTS（$30/月）→ 百炼 TTS" |

### 2.3 ChatterboxTTS 引用

| 文件 | 引用内容 |
|------|----------|
| `SKILL.md` | ChatterboxTTS 作为备选 TTS |

---

## 3. 清理操作清单

### 3.1 删除

| 文件 | 原因 |
|------|------|
| `SKILL.md` | 严重过时（113 行），描述的 Whisper+ElevenLabs+ChatterboxTTS 架构已完全不存在 |

### 3.2 归档标记（顶部添加过时说明）

| 文件 | 标记 |
|------|------|
| `COMPLETION_REPORT.md` | `> **[Archived]** This document is a historical record...` |
| `docs/SESSION_HANDOVER_2026-03-18.md` | 同上 |
| `deploy/runpod/README.md` | 同上 |

### 3.3 微调

| 文件 | 操作 |
|------|------|
| `.github/copilot-instructions.md` | 移除 L43 Faster-Whisper, L94 whisper 备选, L168 faster-whisper, L321 Large Whisper |

---

## 4. 执行状态

- [x] 审查完成
- [ ] 删除 `SKILL.md`
- [ ] 归档标记 3 个文件
- [ ] 微调 `copilot-instructions.md`

---

*本报告与 `AUDIT_CODEBASE_2026-03-23.md` 配套使用。*
