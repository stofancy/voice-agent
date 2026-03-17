# OpenClaw Voice — 项目交接文档（最新版）

更新时间：2026-03-17
分支：`feat/openclaw-low-latency-transport`
状态：后端 E2E 与性能日志体系已完成，下一阶段进入 v2 前端交互优化

---

## 1. 本次交接结论（TL;DR）

- 后端主流程（STT → LLM → TTS）已经具备**真实 Provider 级 E2E 测试能力**。
- 已具备**实时性能日志**（运行中可观察）与**结构化性能报告**（运行后可分析）。
- 已提供**一键执行脚本**，可直接让任何人本地复现实验。
- 下一阶段重点：使用 **Google AI Studio** 生成可交互前端原型，并据此迭代 `src/client/v2/` 页面与交互细节。

---

## 2. 今日完成内容（按交付物）

### 2.1 后端 E2E 测试体系（真实调用）

新增目录与测试：

- `tests/e2e/conftest.py`
- `tests/e2e/test_stt_transcription.py`
- `tests/e2e/test_llm_streaming.py`
- `tests/e2e/test_tts_generation.py`
- `tests/e2e/test_pipeline_e2e.py`

能力覆盖：

- STT 识别延迟、准确率与边界输入
- LLM 流式首 token 延迟（TTFT）、吞吐表现
- TTS 首音频延迟（TTFA）、流式分块时序
- 全链路感知延迟：`STT + LLM_TTFT + TTS_TTFA`

### 2.2 性能日志与报告

新增/强化：

- 实时运行日志：`tests/e2e/test_run.log`
- 指标报告：`tests/e2e/performance_report.json`
- 监控脚本：`scripts/monitor_e2e_tests.sh`

日志特性：

- 测试生命周期日志（开始/通过/失败）
- 组件级耗时日志（STT/LLM/TTS）
- 流式细粒度日志（token/chunk 级）

### 2.3 一键执行入口

新增脚本：

- `scripts/run_e2e_backend.sh`

支持：

- 自动读取 `.env` / `.env.bailian`
- 检查 `ALI_BAILIAN_API_KEY`
- 自动准备 `.venv` 与 pytest 依赖
- 一键全量或按 pattern 执行
- 可选联动实时监控

### 2.4 文档补充

新增测试规范：

- `docs/TESTING_GUIDELINE.md`

包含：

- 测试层级、命令、判定标准、故障分流、报告规范

---

## 3. 关键提交记录（可追溯）

近期关键提交（从旧到新）：

- `e8c8c92` test(e2e): comprehensive backend E2E tests with latency benchmarks
- `c154e1d` test(e2e): add comprehensive real-time performance logging
- `1b3e14e` feat: enhance E2E log monitoring script with usage instructions and improved modes
- `df868cb` docs(test): add backend testing guideline and one-click e2e runner

说明：以上提交已在当前分支并已推送到远端对应分支。

---

## 4. 当前可直接使用的命令

### 4.1 一键执行后端 E2E（推荐）

```bash
./scripts/run_e2e_backend.sh
```

常用：

```bash
# 仅跑某一类/某一文件
./scripts/run_e2e_backend.sh --pattern tests/e2e/test_pipeline_e2e.py

# 边跑边监控
./scripts/run_e2e_backend.sh --monitor
```

### 4.2 运行时查看日志

```bash
# 自动模式
./scripts/monitor_e2e_tests.sh

# 强制持续跟随
./scripts/monitor_e2e_tests.sh --follow

# 一次性查看后退出
./scripts/monitor_e2e_tests.sh --once
```

### 4.3 核心产物位置

- 实时日志：`tests/e2e/test_run.log`
- 性能报告：`tests/e2e/performance_report.json`

---

## 5. 当前状态与已知风险

### 5.1 已知状态

- 后端 E2E 在有效 key 与网络环境下可跑通。
- 测试依赖真实外部服务，耗时和抖动与网络/Provider 负载有关。

### 5.2 已知风险

- 外部 API 波动会导致偶发延迟升高。
- 本地重复运行会刷新音频 fixture 与报告文件，需注意提交噪音。

### 5.3 提交建议

默认不要提交以下运行产物（除非明确需要留档）：

- `tests/e2e/test_run.log*`
- `tests/e2e/performance_report.json`（日常跑测时）
- 仅因临时重跑生成的音频变化

---

## 6. 下一阶段目标（重点）

> 目标：使用 **Google AI Studio** 生成可交互前端原型，并将可用交互与视觉规范下沉到 `src/client/v2/`。

### 6.1 目标拆分

1. 在 AI Studio 快速产出交互原型（语音态、字幕态、中断态、历史折叠态）
2. 固化 UI/交互规格（状态机、组件结构、文案、节奏）
3. 将规格映射到当前 v2 文件结构进行增量改造
4. 用既有后端协议验证联调

### 6.2 交接后的执行路线（建议顺序）

#### Step A — 原型输入准备（0.5 天）

准备给 AI Studio 的输入包：

- 当前页面截图与状态列表
- 现有协议事件清单（`tts_start/tts_end/interrupt/...`）
- 交互目标（延迟感知优化、可中断、可滚动历史）

建议落地文件：

- `docs/ux.html`（作为 UX 说明与资产入口）
- `docs/DESIGN_v2.md`（更新为当前真实状态）

#### Step B — AI Studio 生成交互原型（0.5~1 天）

需要产出：

- 主要状态页面：Idle / Listening / Processing / Speaking / Interrupted
- 关键组件行为：Talk Button、Interrupt Button、Message Bubble
- 文案策略：错误提示、连接状态、重试引导

验收标准：

- 可点击交互，不是纯静态图
- 状态切换路径完整
- 与现有后端事件一一对应

#### Step C — v2 前端增量实现（1~2 天）

对应代码区域：

- `src/client/v2/index.html`
- `src/client/v2/js/app.js`
- `src/client/v2/js/ui.js`
- `src/client/v2/components/*`
- `src/client/v2/css/*`

实现要求：

- 不改后端协议定义
- 先实现状态正确性，再做视觉细节
- 交互变化必须可回归测试（最少手工 checklist）

#### Step D — 联调与验收（0.5 天）

联调维度：

- 连接恢复与重连体验
- 语音中断时 UI 与播放状态一致性
- 字幕/历史面板在移动端与桌面的表现

输出：

- 回归清单
- 体验问题列表（按 P0/P1/P2）

---

## 7. 接手人第一天清单（可直接照做）

1. 拉取分支并确认环境

```bash
git checkout feat/openclaw-low-latency-transport
git pull
```

2. 确认 key 与一键脚本可执行

```bash
./scripts/run_e2e_backend.sh --pattern tests/e2e/test_pipeline_e2e.py
```

3. 查看最近一轮性能基线

- `tests/e2e/performance_report.json`
- `tests/e2e/test_run.log`

4. 阅读并对齐文档

- `docs/TESTING_GUIDELINE.md`
- `docs/DESIGN_v2.md`
- `docs/ux.html`

5. 开始 AI Studio 原型工作（按第 6 节步骤）

---

## 8. 前后端接口对齐提醒（给下一位同学）

前端改造时必须保持以下原则：

- 不擅自新增后端事件名，先复用现有事件
- 视觉状态与后端状态一一映射，避免“看起来在说话但后端已停止”
- 中断逻辑优先级最高（用户说话即中断播报）

如果确需新增协议字段，必须先在文档写清：

- 事件名
- 触发时机
- 前端处理路径
- 向后兼容策略

---

## 9. 相关文件索引

### 测试与脚本

- `scripts/run_e2e_backend.sh`
- `scripts/monitor_e2e_tests.sh`
- `tests/e2e/conftest.py`
- `tests/e2e/test_pipeline_e2e.py`

### 文档

- `docs/TESTING_GUIDELINE.md`
- `docs/V2_EXECUTION_PLAN_FULL_SCOPE.md`
- `docs/DESIGN_v2.md`
- `docs/ux.html`

### 前端 v2

- `src/client/v2/index.html`
- `src/client/v2/js/app.js`
- `src/client/v2/js/ui.js`
- `src/client/v2/components/`
- `src/client/v2/css/`

---

## 10. 交接备注

- 旧版 `HANDOVER.md` 已失效，不应再作为执行依据。
- 本文档为当前唯一有效交接基线。
- 下一阶段如果完成 AI Studio 原型并落地 v2，请在本文件顶部更新时间并追加“变更摘要”。
