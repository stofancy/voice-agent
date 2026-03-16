#!/usr/bin/env node
/**
 * Voice Agent Docker 集成测试
 */

import { WebSocket } from 'ws';

const WS_URL = process.env.VOICE_AGENT_WS_URL || 'ws://localhost:8765/voice-agent/stream';

console.log(`[Test] Connecting to ${WS_URL}...`);

const ws = new WebSocket(WS_URL);

const timeout = setTimeout(() => {
  console.error('[Test] ❌ Connection timeout (30s)');
  ws.close();
  process.exit(1);
}, 30000);

ws.on('open', () => {
  clearTimeout(timeout);
  console.log('[Test] ✅ Connected to Voice Agent');
  console.log('[Test] Waiting for status message...');
});

ws.on('message', (data) => {
  try {
    const message = JSON.parse(data.toString());
    console.log('[Test] Received:', JSON.stringify(message));
    
    if (message.type === 'status') {
      console.log('[Test] ✅ Status received:', message.state);
      console.log('[Test] ✅ Integration test PASSED');
      ws.close();
      process.exit(0);
    }
  } catch (error) {
    console.error('[Test] Parse error:', error.message);
  }
});

ws.on('error', (error) => {
  clearTimeout(timeout);
  console.error('[Test] ❌ WebSocket error:', error.message);
  console.log('[Test] This is expected if Voice Agent plugin is not loaded yet');
  process.exit(1);
});

ws.on('close', () => {
  console.log('[Test] Connection closed');
});
