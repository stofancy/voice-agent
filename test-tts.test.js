#!/usr/bin/env node
/**
 * TTS Client 单元测试
 * 
 * 测试阿里百炼 TTS API 调用
 */

import { TTSClient } from './packages/server/dist/tts/client.js';

const API_KEY = process.env.ALI_BAILIAN_API_KEY || 'sk-your-api-key-here';

async function testTTS() {
  console.log('[TTS Test] Starting...\n');
  
  const client = new TTSClient({
    apiKey: API_KEY,
    model: 'qwen3-tts-instruct-flash',
    voice: 'Cherry',
  });
  
  try {
    // 测试 1: 短文本
    console.log('[Test 1] Short text "你好"...');
    const start1 = Date.now();
    const result1 = await client.synthesize('你好');
    const duration1 = Date.now() - start1;
    
    if (result1.audioData && result1.audioData.length > 0) {
      console.log(`✅ Short text: ${result1.audioData.length} bytes, ${duration1}ms\n`);
    } else {
      console.log(`❌ No audio data returned\n`);
      return false;
    }
    
    // 测试 2: 长文本
    console.log('[Test 2] Long text "欢迎使用 Voice Agent 语音交互系统"...');
    const start2 = Date.now();
    const result2 = await client.synthesize('欢迎使用 Voice Agent 语音交互系统，这是一个基于阿里百炼 STT 和 TTS 的语音交互插件');
    const duration2 = Date.now() - start2;
    
    if (result2.audioData && result2.audioData.length > 0) {
      console.log(`✅ Long text: ${result2.audioData.length} bytes, ${duration2}ms\n`);
    } else {
      console.log(`❌ No audio data returned\n`);
      return false;
    }
    
    // 测试 3: 空文本（应该失败或返回空）
    console.log('[Test 3] Empty text...');
    try {
      const result3 = await client.synthesize('');
      console.log(`✅ Empty text: ${result3.audioData?.length || 0} bytes\n`);
    } catch (error) {
      console.log(`✅ Empty text error (expected): ${error.message}\n`);
    }
    
    console.log('[TTS Test] All tests passed!\n');
    console.log('Performance Summary:');
    console.log(`  Short text: ${duration1}ms`);
    console.log(`  Long text: ${duration2}ms`);
    console.log(`  Average: ${Math.round((duration1 + duration2) / 2)}ms\n`);
    
    return true;
    
  } catch (error) {
    console.error('[TTS Test] Failed:', error);
    return false;
  }
}

// 运行测试
const passed = await testTTS();
process.exit(passed ? 0 : 1);
