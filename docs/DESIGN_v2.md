# OpenClaw Voice v2.0 设计方案

**版本**: v2.0.0-draft  
**创建时间**: 2026-03-17 02:30  
**作者**: 九章  
**状态**: 待评审

---

## 📋 项目概述

### 背景

OpenClaw Voice v1.0 已实现基础功能：
- ✅ 百炼 STT 语音识别
- ✅ 百炼 TTS 语音合成
- ✅ 流式字幕显示
- ✅ 流式 TTS 播放（带缓冲）
- ✅ 配置切换（流式/非流式）

### v2.0 新增需求

| 编号 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| F1 | 用户说话时停止播放 | 🔴 P0 | VAD 检测用户说话时自动暂停 AI 回复 |
| F2 | 打断按钮 | 🔴 P0 | 主动打断 AI 说话 |
| F3 | 富文本字幕 | 🔴 P0 | 支持图片、链接、视频、HTML 格式化 |
| F4 | 说话动画 | 🟡 P1 | AI 说话时 Talk 按钮动画 |
| F5 | 独立 v2 页面 | 🔴 P0 | 与 v1 分开，不影响现有使用 |
| F6 | UI 重新设计 | 🟡 P1 | 简洁、响应式、科技感 |

---

## 🎨 UI/UX 设计方案

### 设计理念

**核心原则**：
- **Mobile First** - 移动端优先，渐进增强
- **简洁高效** - 隐藏不必要的元素，专注核心功能
- **科技感** - 未来感设计，但不失可用性
- **信息密度** - 滚动、折叠、归纳展示丰富信息

### 页面布局

```
┌─────────────────────────────────────────────────────────┐
│  [≡] OpenClaw Voice                    [⚙️] [🌙]        │  ← 顶部栏（可隐藏）
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │                                                 │   │
│  │   📝 对话记录区域（滚动）                        │   │
│  │   ┌─────────────────────────────────────────┐   │   │
│  │   │ 👤 用户：今天天气怎么样？                │   │   │
│  │   └─────────────────────────────────────────┘   │   │
│  │   ┌─────────────────────────────────────────┐   │   │
│  │   │ 🤖 AI：今天北京晴朗，气温 25°C...        │   │   │
│  │   │    [图片：天气预报卡片]                  │   │   │
│  │   │    [链接：查看详情 →]                    │   │   │
│  │   └─────────────────────────────────────────┘   │   │
│  │                                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│              ┌─────────────────────┐                   │
│              │                     │                   │
│              │      🎤 TALK        │  ← Talk 按钮      │
│              │   （说话时动画）     │     带声波动画    │
│              │                     │                   │
│              └─────────────────────┘                   │
│                                                         │
│    [⏹️ 打断]  [📋 历史]  [⚙️ 设置]                      │  ← 功能按钮
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 颜色方案

**主题色**：
- **主色**: `#00D4FF` (科技蓝)
- **强调色**: `#FF006E` (活力粉)
- **背景**: `#0A0A0F` (深空黑)
- **卡片**: `#1A1A2E` (星云紫)
- **文字**: `#FFFFFF` / `#A0A0B0`

**渐变效果**：
```css
background: linear-gradient(135deg, #0A0A0F 0%, #1A1A2E 100%);
accent: linear-gradient(90deg, #00D4FF 0%, #FF006E 100%);
```

### 动画设计

#### 1. Talk 按钮声波动画

**触发条件**：AI 正在说话（TTS 播放中）

**动画效果**：
- 按钮周围脉冲光环
- 3-5 条动态声波线
- 颜色随音量变化

```css
@keyframes pulse-ring {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 212, 255, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 20px rgba(0, 212, 255, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 212, 255, 0); }
}

@keyframes sound-wave {
  0%, 100% { height: 10px; }
  50% { height: 30px; }
}
```

#### 2. 字幕滚动动画

- 新消息从底部滑入
- 旧消息自动折叠（超过 3 条）
- 点击展开历史记录

#### 3. 打断按钮反馈

- 点击时红色闪烁
- 震动反馈（移动端）
- 立即停止 TTS 播放

---

## 🔧 技术方案

### F1: 用户说话时停止播放

**实现方案**：
```javascript
// 前端 VAD 检测
const vad = new VoiceActivityDetector({
  onSpeechStart: () => {
    if (isPlaying) {
      pauseTTS();  // 暂停播放
      showUserSpeakingIndicator();
    }
  },
  onSpeechEnd: () => {
    hideUserSpeakingIndicator();
  }
});
```

**技术栈**：
- `silero-vad` (WebAssembly)
- 浏览器 Web Audio API
- 低延迟检测（<100ms）

### F2: 打断按钮

**实现方案**：
```javascript
// 打断按钮
async function interruptAI() {
  // 1. 立即停止 TTS 播放
  audioElement.pause();
  audioElement.currentTime = 0;
  
  // 2. 发送打断信号到后端
  await websocket.send(JSON.stringify({
    type: 'interrupt',
    timestamp: Date.now()
  }));
  
  // 3. 清除待播放队列
  audioQueue = [];
  
  // 4. UI 反馈
  showInterruptedState();
}
```

**后端支持**：
```python
# main.py
elif msg["type"] == "interrupt":
    logger.info("🔴 用户打断 AI 说话")
    # 停止当前 TTS 生成
    tts_generation_cancelled = True
```

### F3: 富文本字幕

**实现方案**：
```javascript
// 支持的消息类型
{
  "type": "response_chunk",
  "content": [
    { "type": "text", "text": "今天天气晴朗..." },
    { "type": "image", "url": "https://...", "alt": "天气预报" },
    { "type": "link", "url": "https://...", "text": "查看详情" },
    { "type": "video", "url": "https://...", "thumbnail": "..." },
    { "type": "html", "html": "<b>格式化</b> 文本" }
  ]
}
```

**渲染组件**：
```jsx
<Message content={message.content}>
  {content.map(block => {
    switch(block.type) {
      case 'text': return <TextBlock text={block.text} />
      case 'image': return <ImageBlock src={block.url} />
      case 'link': return <LinkBlock href={block.url} />
      case 'video': return <VideoBlock src={block.url} />
      case 'html': return <HTMLBlock html={block.html} />
    }
  })}
</Message>
```

**后端支持**：
```python
#  Gateway 返回结构化内容
{
  "content": [
    {"type": "text", "text": "..."},
    {"type": "image", "url": "..."},
  ]
}
```

### F4: 说话动画

**实现方案**：
```javascript
// WebSocket 消息
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  if (msg.type === 'tts_start') {
    talkButton.classList.add('speaking');
  }
  if (msg.type === 'tts_end') {
    talkButton.classList.remove('speaking');
  }
};
```

**CSS 动画**：
```css
.talk-button.speaking {
  animation: pulse-ring 1.5s infinite;
}

.talk-button.speaking::before {
  content: '';
  position: absolute;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, rgba(0,212,255,0.3) 0%, transparent 70%);
  animation: sound-wave 0.5s infinite;
}
```

### F5: 独立 v2 页面

**目录结构**：
```
src/client/
├── index.html          # v1.0 (保持不变)
├── v2/
│   ├── index.html      # v2.0 主页面
│   ├── css/
│   │   ├── main.css    # 主样式
│   │   ├── animation.css
│   │   └── mobile.css  # 移动端优化
│   ├── js/
│   │   ├── app.js      # 主应用
│   │   ├── vad.js      # VAD 检测
│   │   ├── tts.js      # TTS 控制
│   │   └── ui.js       # UI 组件
│   └── components/
│       ├── MessageBubble.js
│       ├── TalkButton.js
│       └── InterruptButton.js
```

**访问方式**：
- v1.0: `http://localhost:8765/`
- v2.0: `http://localhost:8765/v2/`

### F6: UI 重新设计

**设计要点**：

1. **简洁**：
   - 隐藏标题（滚动时自动隐藏）
   - 移除 Guideline 等不必要元素
   - 最小化按钮数量

2. **响应式**：
   ```css
   /* Mobile First */
   .container { padding: 10px; }
   
   @media (min-width: 768px) {
     .container { padding: 20px; max-width: 600px; margin: 0 auto; }
   }
   ```

3. **科技感**：
   - 深色主题
   - 渐变效果
   - 玻璃态卡片

4. **信息密度**：
   - 滚动字幕（超过 3 条自动折叠）
   - 点击展开历史
   - 智能归纳长文本

---

## 📱 响应式设计

### 断点

| 断点 | 宽度 | 布局 |
|------|------|------|
| Mobile | < 768px | 单列，全屏按钮 |
| Tablet | 768-1024px | 单列，侧边按钮 |
| Desktop | > 1024px | 最大宽度 600px，居中 |

### 移动端优化

- Touch-friendly 按钮（最小 44x44px）
- 手势支持（滑动删除消息）
- 全屏模式（隐藏浏览器 UI）

---

## 🔒 安全考虑

- XSS 防护（富文本内容过滤）
- CSP 策略（限制外部资源）
- WebSocket 认证（可选）

---

## 📊 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 首屏加载 | < 1s | 无外部依赖 |
| VAD 延迟 | < 100ms | 实时检测 |
| 打断响应 | < 200ms | 立即停止 |
| 动画帧率 | 60fps | 流畅动画 |

---

## 🎯 验收标准

### F1: 用户说话时停止播放
- [ ] VAD 检测准确率 > 90%
- [ ] 暂停延迟 < 200ms
- [ ] 恢复播放正常

### F2: 打断按钮
- [ ] 点击立即停止 TTS
- [ ] 视觉反馈明显
- [ ] 后端正确处理打断信号

### F3: 富文本字幕
- [ ] 支持文本、图片、链接、视频
- [ ] HTML 格式化正常渲染
- [ ] XSS 防护有效

### F4: 说话动画
- [ ] AI 说话时按钮动画
- [ ] 动画流畅（60fps）
- [ ] 不消耗过多性能

### F5: 独立 v2 页面
- [ ] v1.0 正常工作
- [ ] v2.0 独立访问
- [ ] 无冲突

### F6: UI 重新设计
- [ ] 移动端友好
- [ ] 响应式布局
- [ ] 科技感设计
- [ ] 信息展示充分

---

*文档创建：2026-03-17 02:30*  
*下次更新：评审后*
