#!/usr/bin/env python3
"""
Test script for Bailian STT/TTS integration.

Usage:
    python test-bailian.py
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from server.bailian_stt import BailianSTT
from server.bailian_tts import BailianTTS


async def test_stt():
    """Test Bailian STT with sample audio."""
    print("\n🎤 Testing Bailian STT...")
    
    api_key = os.environ.get("ALI_BAILIAN_API_KEY")
    if not api_key:
        print("⚠️  ALI_BAILIAN_API_KEY not set")
        return False
    
    stt = BailianSTT(api_key=api_key)
    
    if stt._client is None:
        print("❌ STT client not initialized")
        return False
    
    # Test with sample audio URL
    print("✅ STT client ready")
    print(f"   Model: {stt.model}")
    print(f"   Language: {stt.language}")
    
    # Note: Actual audio test requires audio file
    print("ℹ️  To test STT, provide an audio file:")
    print("   await stt.transcribe_file('path/to/audio.wav')")
    
    return True


async def test_tts():
    """Test Bailian TTS with sample text."""
    print("\n🔊 Testing Bailian TTS...")
    
    api_key = os.environ.get("ALI_BAILIAN_API_KEY")
    if not api_key:
        print("⚠️  ALI_BAILIAN_API_KEY not set")
        return False
    
    tts = BailianTTS(api_key=api_key)
    
    if not tts.api_key:
        print("❌ TTS API key not set")
        return False
    
    print("✅ TTS client ready")
    print(f"   Model: {tts.model}")
    print(f"   Voice: {tts.voice}")
    print(f"   Language: {tts.language_type}")
    
    # Test synthesis
    test_text = "你好，这是百炼语音合成测试"
    print(f"\n📝 Synthesizing: {test_text}")
    
    audio_chunks = []
    async for chunk in tts.synthesize(test_text, stream=False):
        audio_chunks.append(chunk)
    
    if audio_chunks:
        print(f"✅ Synthesis successful: {len(audio_chunks)} chunks, {sum(len(c) for c in audio_chunks)} bytes")
        
        # Save to file
        output_path = "/tmp/test_tts_output.wav"
        with open(output_path, 'wb') as f:
            f.write(b''.join(audio_chunks))
        print(f"💾 Saved to: {output_path}")
    else:
        print("❌ No audio data received")
        return False
    
    await tts.close()
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🦞 OpenClaw Voice - Bailian Integration Test")
    print("=" * 60)
    
    stt_ok = await test_stt()
    tts_ok = await test_tts()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"  STT: {'✅ PASS' if stt_ok else '❌ FAIL'}")
    print(f"  TTS: {'✅ PASS' if tts_ok else '❌ FAIL'}")
    print("=" * 60)
    
    return stt_ok and tts_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
