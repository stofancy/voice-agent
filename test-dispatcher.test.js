#!/usr/bin/env node
/**
 * Dispatcher 单元测试
 * 
 * 测试 Agent 回复 → TTS → WebSocket 流程
 */

import { WebSocket } from 'ws';
import { TTSClient } from './src/tts/client.js';
import { createVoiceAgentDispatcher } from './src/messaging/inbound/dispatcher.js';

const API_KEY = process.env.ALI_BAILIAN_API_KEY || 'sk-your-api-key-here';

async function testDispatcher() {
  console.log('[Dispatcher Test] Starting...\n');
  
  // 创建 mock WebSocket 服务器
  const wss = new WebSocket.Server({ port: 0 });
  const testPort = wss.address().port;
  
  console.log(`[Mock Server] Listening on port ${testPort}\n`);
  
  let receivedMessages = [];
  
  wss.on('connection', (ws) => {
    console.log('[Mock Server] Client connected\n');
    
    ws.on('message', (data) => {
      const message = JSON.parse(data.toString());
      receivedMessages.push(message);
      console.log(`[Mock Server] Received: ${message.type}`, message.data ? JSON.stringify(message.data).substring(0, 100) : '');
    });
    
    ws.on('close', () => {
      console.log('[Mock Server] Client disconnected\n');
    });
  });
  
  // 创建客户端连接
  const clientWs = new WebSocket(`ws://localhost:${testPort}`);
  
  await new Promise((resolve) => {
    clientWs.on('open', resolve);
  });
  
  console.log('[Test 1] Create dispatcher...');
  const ttsClient = new TTSClient({
    apiKey: API_KEY,
    model: 'qwen3-tts-instruct-flash',
    voice: 'Cherry',
  });
  
  const { dispatcher, waitForIdle, markDispatchIdle, markFullyComplete } = 
    createVoiceAgentDispatcher(clientWs, 'test-session', ttsClient);
  
  console.log('✅ Dispatcher created\n');
  
  try {
    // 测试 2: 发送 Agent 回复
    console.log('[Test 2] Send Agent reply "你好"...');
    const start = Date.now();
    
    await dispatcher({
      text: '你好',
      final: true,
      messageId: 'test-1',
    });
    
    await waitForIdle();
    markFullyComplete();
    markDispatchIdle();
    
    const duration = Date.now() - start;
    console.log(`✅ Agent reply processed in ${duration}ms\n`);
    
    // 验证收到的消息
    console.log('[Test 3] Verify messages...');
    console.log(`  Received ${receivedMessages.length} messages`);
    
    const hasStatus = receivedMessages.some(m => m.type === 'status');
    const hasText = receivedMessages.some(m => m.type === 'agent_text');
    const hasAudio = receivedMessages.some(m => m.type === 'agent_audio');
    
    console.log(`  Status message: ${hasStatus ? '✅' : '❌'}`);
    console.log(`  Text message: ${hasText ? '✅' : '❌'}`);
    console.log(`  Audio message: ${hasAudio ? '✅' : '❌'}`);
    
    if (hasStatus && hasText && hasAudio) {
      console.log('\n[Dispatcher Test] All tests passed!\n');
      
      // 清理
      clientWs.close();
      wss.close();
      
      return true;
    } else {
      console.log('\n[Dispatcher Test] Some tests failed!\n');
      return false;
    }
    
  } catch (error) {
    console.error('[Dispatcher Test] Failed:', error);
    
    // 清理
    clientWs.close();
    wss.close();
    
    return false;
  }
}

// 运行测试
const passed = await testDispatcher();
process.exit(passed ? 0 : 1);
