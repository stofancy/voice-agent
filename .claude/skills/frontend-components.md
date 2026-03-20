# Frontend Components 技能

## 概述
本技能指导如何理解和使用 voice-agent 项目的前端组件。

## 项目结构
- 前端资源: `src/client/v2/`
- 组件目录: `src/client/v2/components/`
- 样式目录: `src/client/v2/css/`
- JavaScript: `src/client/v2/js/`

## 组件架构

### 模块模式
组件使用 IIFE (立即调用函数表达式) 模式:

```javascript
(function () {
    function MyComponent(element) {
        this.element = element;
    }

    MyComponent.prototype.method = function () {
        // 实现
    };

    window.MyComponent = MyComponent;
})();
```

### TalkButton 组件
```javascript
(function () {
    function TalkButton(element) {
        this.element = element;
    }

    TalkButton.prototype.setListening = function (listening) {
        this.element.classList.toggle('listening', Boolean(listening));
    };

    TalkButton.prototype.setSpeaking = function (speaking) {
        this.element.classList.toggle('speaking', Boolean(speaking));
    };

    window.TalkButton = TalkButton;
})();
```

### 使用
```javascript
const button = document.getElementById('talk-btn');
const talkButton = new TalkButton(button);
talkButton.setListening(true);  // 添加 listening class
talkButton.setSpeaking(true);  // 添加 speaking class
```

## 消息气泡组件 (MessageBubble)

### 渲染器模式
```javascript
const renderers = {
    text: (block) => `<p>${block.text}</p>`,
    image: (block) => `<img src="${block.url}" alt="${block.alt}">`,
    link: (block) => `<a href="${block.url}">${block.text}</a>`,
    video: (block) => `<video src="${block.url}" title="${block.title}">`,
    html: (block) => `<div>${block.html}</div>`,
};

function renderBlock(block) {
    const renderer = renderers[block.type];
    return renderer ? renderer(block) : '';
}
```

### 创建消息元素
```javascript
function createMessageElement(role, payload) {
    const message = document.createElement('div');
    message.className = `message ${role === 'user' ? 'user' : 'assistant'}`;

    const content = document.createElement('div');
    content.className = 'message-content';

    const sender = document.createElement('span');
    sender.className = 'message-sender';
    sender.textContent = role === 'user' ? '👤 用户' : '🤖 AI';

    content.appendChild(sender);

    // 渲染内容块
    if (Array.isArray(payload)) {
        const html = payload.map(renderBlock).join('');
        content.insertAdjacentHTML('beforeend', html);
    } else {
        const blocks = window.SanitizeUtils.parseTextToBlocks(String(payload));
        const html = blocks.map(renderBlock).join('');
        content.insertAdjacentHTML('beforeend', html);
    }

    message.appendChild(content);
    return message;
}

window.MessageBubble = { createMessageElement };
```

## 块组件 (Blocks)

### TextBlock
```javascript
window.TextBlock = function(text) {
    return `<p class="message-text">${window.SanitizeUtils.renderMarkdownLite(text)}</p>`;
};
```

### ImageBlock
```javascript
window.ImageBlock = function(url, alt) {
    if (!url) return '';
    return `<img class="message-image" src="${url}" alt="${alt || ''}" loading="lazy">`;
};
```

### LinkBlock
```javascript
window.LinkBlock = function(url, text) {
    return `<a class="message-link" href="${url}" target="_blank" rel="noopener">${text}</a>`;
};
```

### VideoBlock
```javascript
window.VideoBlock = function(url, title) {
    return `<video class="message-video" src="${url}" title="${title || ''}" controls></video>`;
};
```

### HtmlBlock
```javascript
window.HtmlBlock = function(html) {
    return `<div class="message-html">${html}</div>`;
};
```

## WebSocket 客户端

### 连接管理
```javascript
class VoiceClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.state = 'idle';
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('Connected');
            this.state = 'connected';
        };

        this.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            this.handleMessage(msg);
        };

        this.ws.onclose = () => {
            console.log('Disconnected');
            this.state = 'disconnected';
        };
    }

    handleMessage(msg) {
        switch (msg.type) {
            case 'listening_started':
                this.state = 'listening';
                break;
            case 'transcript':
                console.log('Transcript:', msg.text);
                break;
            case 'subtitle_chunk':
                this.updateSubtitle(msg.text);
                break;
            case 'audio_chunk':
                this.playAudio(msg.data, msg.sample_rate);
                break;
            case 'tts_start':
                this.state = 'speaking';
                break;
            case 'tts_end':
                this.state = 'idle';
                break;
        }
    }

    startListening() {
        this.ws.send(JSON.stringify({ type: 'start_listening' }));
    }

    stopListening() {
        this.ws.send(JSON.stringify({ type: 'stop_listening' }));
    }

    sendAudio(audioData) {
        // audioData 是 float32 数组的 base64 编码
        this.ws.send(JSON.stringify({
            type: 'audio',
            data: audioData
        }));
    }

    interrupt() {
        this.ws.send(JSON.stringify({ type: 'interrupt' }));
    }
}
```

### 音频播放
```javascript
class AudioPlayer {
    constructor() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.queue = [];
        this.isPlaying = false;
    }

    playChunk(base64Data, sampleRate) {
        const audioData = this.base64ToFloat32(base64Data);
        this.queue.push({ data: audioData, sampleRate });
        this.processQueue();
    }

    base64ToFloat32(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        const float32 = new Float32Array(bytes.buffer);
        return float32;
    }

    async processQueue() {
        if (this.isPlaying || this.queue.length === 0) return;

        this.isPlaying = true;

        while (this.queue.length > 0) {
            const { data, sampleRate } = this.queue.shift();
            await this.playBuffer(data, sampleRate);
        }

        this.isPlaying = false;
    }

    playBuffer(data, sampleRate) {
        return new Promise((resolve) => {
            const buffer = this.audioContext.createBuffer(
                1,  // 单声道
                data.length,
                sampleRate
            );
            buffer.getChannelData(0).set(data);

            const source = this.audioContext.createBufferSource();
            source.buffer = buffer;
            source.connect(this.audioContext.destination);

            source.onended = resolve;
            source.start();
        });
    }
}
```

## 音频录制

### MediaRecorder API
```javascript
class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
    }

    async start() {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.mediaRecorder = new MediaRecorder(stream);
        this.audioChunks = [];

        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                this.audioChunks.push(event.data);
            }
        };

        this.mediaRecorder.start(100);  // 每 100ms 收集一次
    }

    stop() {
        return new Promise((resolve) => {
            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                resolve(audioBlob);
            };
            this.mediaRecorder.stop();
        });
    }

    async getFloat32Array(audioBlob) {
        const arrayBuffer = await audioBlob.arrayBuffer();
        const audioContext = new AudioContext();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        return audioBuffer.getChannelData(0);  // Float32Array
    }
}
```

## 样式指南

### CSS 变量
```css
:root {
    --primary-color: #007AFF;
    --background: #000000;
    --surface: #1C1C1E;
    --text: #FFFFFF;
    --text-secondary: #8E8E93;
}
```

### 状态样式
```css
.listening {
    animation: pulse 1.5s infinite;
    background: var(--primary-color);
}

.speaking {
    animation: ripple 1s infinite;
    background: #34C759;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
}
```

## 工具函数

### SanitizeUtils
```javascript
window.SanitizeUtils = {
    parseTextToBlocks(text) {
        // 文本解析为块
        const blocks = [];
        // ... 解析逻辑
        return blocks;
    },

    renderMarkdownLite(text) {
        // 简单的 Markdown 渲染
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }
};
```
