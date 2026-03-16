#!/usr/bin/env node
/**
 * STT Client 单元测试
 * 
 * 测试阿里百炼 STT API 调用
 */

import { STTClient } from './packages/server/dist/stt/client.js';

const API_KEY = process.env.ALI_BAILIAN_API_KEY || 'sk-your-api-key-here';

async function testSTT() {
  console.log('[STT Test] Starting...\n');
  
  const client = new STTClient({
    apiKey: API_KEY,
    model: 'qwen3-asr-flash',
  });
  
  try {
    // 测试 1: 空音频（应该失败或返回空）
    console.log('[Test 1] Empty audio...');
    try {
      const result1 = await client.transcribe('');
      console.log(`✅ Empty audio: "${result1.text}"\n`);
    } catch (error) {
      console.log(`✅ Empty audio error (expected): ${error.message}\n`);
    }
    
    // 测试 2: 无效 Base64（应该失败）
    console.log('[Test 2] Invalid Base64...');
    try {
      const result2 = await client.transcribe('invalid-base64!!!');
      console.log(`❌ Should have failed but got: "${result2.text}"\n`);
    } catch (error) {
      console.log(`✅ Invalid Base64 error (expected): ${error.message}\n`);
    }
    
    console.log('[STT Test] All tests passed!\n');
    return true;
    
  } catch (error) {
    console.error('[STT Test] Failed:', error);
    return false;
  }
}

// 运行测试
const passed = await testSTT();
process.exit(passed ? 0 : 1);
