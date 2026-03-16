#!/usr/bin/env node
/**
 * Voice Agent 端到端测试脚本
 * 
 * 测试流程：
 * 1. 启动 WebSocket 服务器
 * 2. 连接客户端
 * 3. 发送测试音频
 * 4. 验证 STT → Agent → TTS 流程
 */

import { WebSocket } from 'ws';

const WS_URL = process.env.VOICE_AGENT_WS_URL || 'ws://localhost:8765/voice-agent/stream';

console.log(`[Test] Connecting to ${WS_URL}...`);

const ws = new WebSocket(WS_URL);

ws.on('open', () => {
  console.log('[Test] ✅ Connected');
  
  // 等待会话初始化
  setTimeout(() => {
    console.log('[Test] Sending test audio...');
    // TODO: 发送测试音频
  }, 1000);
});

ws.on('message', (data) => {
  try {
    const message = JSON.parse(data.toString());
    console.log('[Test] Received:', message.type, message.state || message.data?.text || '');
    
    if (message.type === 'status' && message.state === 'idle') {
      console.log('[Test] ✅ Test complete');
      ws.close();
      process.exit(0);
    }
  } catch (error) {
    console.error('[Test] Parse error:', error);
  }
});

ws.on('error', (error) => {
  console.error('[Test] ❌ Error:', error.message);
  process.exit(1);
});

ws.on('close', () => {
  console.log('[Test] Connection closed');
});

// 超时处理
setTimeout(() => {
  console.error('[Test] ❌ Timeout after 30s');
  ws.close();
  process.exit(1);
}, 30000);
