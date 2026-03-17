# v2 前端重构计划 (React + Tailwind)

**创建时间**: 2026-03-18 00:35
**更新时间**: 2026-03-18 00:40
**状态**: 待批准
**目标**: 基于 v1 功能 + v2 原型设计，采用 React+Tailwind 全面重构前端

---

## 📊 现状分析

### v1 当前实现 (`src/client/index.html`)
| 特性 | 状态 | 说明 |
|------|------|------|
| **架构** | 单文件 HTML | 所有 CSS/JS 内联 |
| **Push-to-talk** | ✅ | 按住说话，松开停止 |
| **Continuous Mode** | ✅ | 免提模式，自动监听 |
| **WebSocket 通信** | ✅ | 流式音频/字幕 |
| **状态显示** | ✅ | 简单文本状态 |
| **转录显示** | ✅ | 简单对话历史 |
| **Markdown 渲染** | ✅ | 基础 Markdown 支持 |
| **WAV 检测** | ✅ | 自动检测 WAV/PCM |
| **视觉设计** | 🟡 基础 | 渐变背景、圆形按钮 |

### v2 原型设计 (`v2_ui_design_extracted/app/`)
| 特性 | 状态 | 说明 |
|------|------|------|
| **架构** | React + TypeScript | 组件化、类型安全 |
| **样式** | Tailwind CSS | 原子化 CSS |
| **动画** | framer-motion | 平滑过渡、幻灯片 |
| **状态机** | ✅ | idle → listening → processing → speaking |
| **VoiceButton** | ✅ | 带动画的语音按钮 |
| **Waveform** | ✅ | 声波动画 |
| **ContentPanel** | ✅ | 内容面板（目的地/酒店/航班） |
| **背景轮播** | ✅ | 热门目的地轮播 |
| **设置 Drawer** | ✅ | 字幕/语音播报开关 |
| **历史 Drawer** | ✅ | 对话历史侧边栏 |

### 现有 v2 原生实现 (`src/client/v2/`)
| 特性 | 状态 | 说明 |
|------|------|------|
| **架构** | 原生 JS | 组件化但未用框架 |
| **样式** | CSS | main/animation/theme/mobile |
| **组件** | ✅ | TalkButton/InterruptButton/MessageBubble |
| **状态** | ⏳ | 框架已建，待完善 |

---

## 🎯 重构目标

### 核心原则
1. **保证需求** — v1 功能必须全部保留（Push-to-talk、Continuous Mode、WebSocket、流式音频/字幕）
2. **分步骤** — 任务拆解至 30 分钟内可完成
3. **小步迭代** — 每个 commit 只修改一个逻辑单元
4. **随时验证** — 每步完成后可独立测试
5. **复用原型** — 最大化复用 `v2_ui_design_extracted/app/` 代码

### 技术栈选择（已更新）
| 组件 | 技术选型 | 说明 |
|------|---------|------|
| **框架** | React 19 | 组件化、状态管理 |
| **语言** | TypeScript | 类型安全 |
| **样式** | Tailwind CSS | 原子化 CSS，快速开发 |
| **动画** | framer-motion | 平滑过渡、手势动画 |
| **构建** | Vite | 快速 HMR、生产优化 |
| **图标** | lucide-react | 现代图标库 |

**决策理由**（主公指示）：
- ✅ v2 原型代码可直接复用，减少开发量
- ✅ React 组件化架构更易维护和扩展
- ✅ Tailwind 快速迭代视觉设计
- ✅ framer-motion 实现流畅动画

---

## 📋 任务拆解

### Phase 0: React+Tailwind 环境搭建（预计 1 小时）

#### Step 0.1: 创建 Vite + React + TypeScript 项目
- **任务**: 在 `src/client/v2-react/` 创建新项目
- **命令**: `npm create vite@latest . -- --template react-ts`
- **输出**: 基础项目结构
- **验证**: `npm run dev` 可启动
- **预计**: 15 分钟

#### Step 0.2: 配置 Tailwind CSS
- **任务**: 安装并配置 Tailwind
- **依赖**: `tailwindcss postcss autoprefixer`
- **输出**: `tailwind.config.js`, `postcss.config.js`
- **验证**: Tailwind 类可用
- **预计**: 15 分钟

#### Step 0.3: 安装 framer-motion 和 lucide-react
- **任务**: 安装动画和图标库
- **依赖**: `framer-motion lucide-react`
- **输出**: 依赖安装完成
- **验证**: 组件可导入
- **预计**: 10 分钟

#### Step 0.4: 复用原型代码
- **任务**: 复制 `v2_ui_design_extracted/app/src/` 到 `src/client/v2-react/src/`
- **输出**: 组件/样式/钩子就绪
- **验证**: 项目可编译
- **预计**: 20 分钟

---

### Phase 1: 核心功能移植（预计 3 小时）

#### Step 1.1: WebSocket 通信层
- **任务**: 移植 v1 WebSocket 逻辑到 React Hook
- **输出**: `hooks/useWebSocket.ts`
- **功能**: 连接/重连、消息处理、错误处理
- **验证**: 可连接后端
- **预计**: 45 分钟

#### Step 1.2: 音频捕获与流式发送
- **任务**: 移植音频捕获逻辑
- **输出**: `hooks/useAudioCapture.ts`
- **功能**: 麦克风权限、音频录制、流式发送
- **验证**: 音频可发送到后端
- **预计**: 45 分钟

#### Step 1.3: 音频播放队列
- **任务**: 移植音频播放队列逻辑
- **输出**: `hooks/useAudioPlayback.ts`
- **功能**: 音频队列、流式播放、WAV/PCM 检测
- **验证**: 音频可正常播放
- **预计**: 45 分钟

#### Step 1.4: 状态机集成
- **任务**: 整合状态机（idle/listening/processing/speaking）
- **输出**: `hooks/useVoiceState.ts`
- **功能**: 状态管理、状态切换
- **验证**: 状态切换正确
- **预计**: 45 分钟

---

### Phase 2: 组件适配（预计 3 小时）

#### Step 2.1: VoiceButton 组件适配
- **任务**: 修改原型 VoiceButton 适配实际功能
- **输入**: `v2_ui_design_extracted/app/src/components/VoiceButton.tsx`
- **输出**: 适配 WebSocket/音频逻辑的 VoiceButton
- **验证**: 按钮可触发录音
- **预计**: 45 分钟

#### Step 2.2: Waveform 组件适配
- **任务**: 修改原型 Waveform 适配状态机
- **输入**: `v2_ui_design_extracted/app/src/components/Waveform.tsx`
- **输出**: 根据 voiceState 显示动画
- **验证**: listening 状态时动画播放
- **预计**: 30 分钟

#### Step 2.3: ContentPanel 组件简化
- **任务**: 简化原型 ContentPanel（移除旅行特定内容）
- **输入**: `v2_ui_design_extracted/app/src/components/ContentPanel.tsx`
- **输出**: 通用消息内容面板
- **验证**: 可显示文本/Markdown
- **预计**: 45 分钟

#### Step 2.4: 设置/历史 Drawer 适配
- **任务**: 修改 Drawer 组件适配实际功能
- **输出**: 字幕开关、清除历史等功能
- **验证**: Drawer 功能正常
- **预计**: 45 分钟

---

### Phase 3: v1 功能对齐（预计 2 小时）

#### Step 3.1: Push-to-talk 实现
- **任务**: 实现按住说话、松开停止
- **输出**: VoiceButton 鼠标/触摸事件处理
- **验证**: 功能与 v1 一致
- **预计**: 30 分钟

#### Step 3.2: Continuous Mode 实现
- **任务**: 实现免提连续对话模式
- **输出**: Continuous Mode 开关 + 自动监听逻辑
- **验证**: 说完自动开始下一句
- **预计**: 45 分钟

#### Step 3.3: 流式字幕实现
- **任务**: 实现 `subtitle_chunk` 实时显示
- **输出**: 流式字幕组件
- **验证**: 字幕实时滚动
- **预计**: 30 分钟

#### Step 3.4: Markdown 渲染
- **任务**: 实现 Markdown 渲染（代码块/链接/粗体等）
- **输出**: Markdown 渲染组件
- **验证**: Markdown 格式正确
- **预计**: 15 分钟

---

### Phase 4: 后端协议扩展（与前端并行，预计 2 小时）

**参考**: `V2_EXECUTION_PLAN_FULL_SCOPE.md` Phase B

#### Step 4.1: 添加 `/v2` 路由
- **任务**: 后端添加 `/v2` 和 `/v2/` 路由
- **输出**: 返回 React 构建的 index.html
- **验证**: 访问 `/v2` 可加载页面
- **预计**: 20 分钟

#### Step 4.2: 添加 interrupt 事件
- **任务**: 后端支持 `interrupt` 输入事件
- **输出**: interrupt_ack, interrupt_complete 输出事件
- **验证**: 打断功能正常
- **预计**: 45 分钟

#### Step 4.3: 添加 tts_start/tts_end 事件
- **任务**: 后端在 TTS 开始/结束时发送事件
- **输出**: tts_start, tts_end 事件
- **验证**: 前端可接收事件
- **预计**: 30 分钟

#### Step 4.4: 添加连接状态守卫
- **任务**: 后端添加会话状态管理（IDLE/LISTENING/PROCESSING/SPEAKING）
- **输出**: 状态守卫逻辑
- **验证**: 无状态冲突
- **预计**: 25 分钟

---

### Phase 5: 测试与验收（预计 1.5 小时）

#### Step 5.1: 功能回归测试
- **任务**: 验证 v1 所有功能正常
- **清单**: Push-to-talk、Continuous Mode、WebSocket、流式音频/字幕
- **预计**: 30 分钟

#### Step 5.2: 视觉验收
- **任务**: 对比 v2 原型，确保视觉一致
- **预计**: 20 分钟

#### Step 5.3: 性能测试
- **任务**: 测试动画性能、内存占用
- **验证**: 60fps 流畅动画
- **预计**: 20 分钟

#### Step 5.4: 文档更新
- **任务**: 更新 README、TODOS.md、HANDOVER.md
- **预计**: 10 分钟

---

## 📊 任务总览

| Phase | 任务数 | 预计时间 | 优先级 |
|-------|-------|---------|--------|
| Phase 0: 环境搭建 | 4 | 1 小时 | 🔴 高 |
| Phase 1: 核心功能移植 | 4 | 3 小时 | 🔴 高 |
| Phase 2: 组件适配 | 4 | 3 小时 | 🔴 高 |
| Phase 3: v1 功能对齐 | 4 | 2 小时 | 🔴 高 |
| Phase 4: 后端协议扩展 | 4 | 2 小时 | 🟡 中 |
| Phase 5: 测试验收 | 4 | 1.5 小时 | 🔴 高 |
| **总计** | **24** | **12.5 小时** | - |

---

## 🔄 执行流程

```
每个 Step 执行流程:
1. 九章派发任务给 Claude ACP
2. Claude ACP 编写代码
3. Claude ACP 提交 (commit)
4. 九章 Code Review (遵循 REVIEW_RULES.md)
5a. 有缺陷 → 返回 Step 2 修复
5b. 通过 → Push 代码
6. 九章阶段验收
7. 完成 → 进入 Next Step
```

---

## ✅ 验收标准

### 功能验收
- [ ] Push-to-talk 正常工作
- [ ] Continuous Mode 正常工作
- [ ] WebSocket 连接稳定
- [ ] 流式音频播放流畅
- [ ] 流式字幕实时显示
- [ ] WAV/PCM 自动检测

### 视觉验收
- [ ] 背景轮播流畅
- [ ] VoiceButton 动画与 v2 一致
- [ ] Waveform 声波动画流畅
- [ ] 状态机显示清晰
- [ ] Drawer 动画平滑

### 代码质量
- [ ] 代码结构清晰（CSS/JS 分离）
- [ ] 无 console 错误
- [ ] 移动端适配良好
- [ ] 每个 commit 可独立回滚

---

## 📝 备注

### 技术决策（已更新）
1. **采用 React+Tailwind** — 复用 v2 原型代码，主公指示
2. **使用 framer-motion** — 原型已用，动画流畅
3. **Vite 构建** — 快速 HMR，生产优化
4. **TypeScript** — 类型安全，减少错误

### 复用策略
- **直接复用**: `v2_ui_design_extracted/app/src/` 中的组件/样式/钩子
- **修改适配**: 将旅行助手逻辑改为通用语音助手逻辑
- **新增功能**: WebSocket 通信、音频捕获/播放等 v1 核心功能

### 风险点
1. **构建复杂度** — 需配置 Docker 构建流程
2. **依赖管理** — npm 依赖需添加到 requirements.txt 或单独构建
3. **移动端兼容** — 需测试 iOS/Android 浏览器

### 后端协同
- Phase 4 后端协议扩展与前端开发并行
- 后端变更需保证 v1 兼容性（additive only）
- 参考 `V2_EXECUTION_PLAN_FULL_SCOPE.md`

### 待确认
- [x] ~~主公是否同意技术栈选择（React+Tailwind）？~~ ✅ 已批准
- [ ] 是否需要优先实现某些 Phase？
- [ ] Docker 构建流程如何安排？

---

**下一步**: 主公批准计划 → 启动 Phase 0 Step 0.1（Vite 项目创建）
