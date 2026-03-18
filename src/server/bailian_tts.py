"""
Text-to-Speech module using Alibaba Bailian (Qwen-TTS).

支持百炼 API：
- 模型：qwen3-tts-flash / qwen3-tts-instruct-flash
- 接入方式：DashScope API
- URL: https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation
- 音色：Cherry, Bella, 等
"""

import asyncio
import base64
import os
import aiohttp
from typing import Optional, AsyncGenerator
from loguru import logger


class BailianTTS:
    """百炼语音合成（Qwen-TTS）"""
    
    # 可用音色列表
    AVAILABLE_VOICES = {
        "Cherry": "甜美女性",
        "Bella": "温柔女性",
        "Sarah": "成熟女性",
        "Jack": "沉稳男性",
        "Allie": "活泼女性",
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen3-tts-flash",
        voice: str = "Cherry",
        language_type: str = "Chinese",
    ):
        self.api_key = api_key or os.environ.get("ALI_BAILIAN_API_KEY")
        self.model = model
        self.voice = voice
        self.language_type = language_type
        self._session: Optional[aiohttp.ClientSession] = None
        
        # 百炼 TTS API URL（北京地域）
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        
        if not self.api_key:
            raise ValueError("ALI_BAILIAN_API_KEY not set - TTS requires Bailian API key")
        else:
            logger.info(f"✅ 百炼 TTS 就绪 (模型：{self.model}, 音色：{self.voice})")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取 HTTP 会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def synthesize(
        self,
        text: str,
        stream: bool = False,
    ) -> AsyncGenerator[bytes, None]:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            stream: 是否流式输出
        
        Yields:
            PCM 音频数据块
        """
        if not self.api_key:
            raise RuntimeError("TTS not initialized - check ALI_BAILIAN_API_KEY")
        
        try:
            session = await self._get_session()
            
            # 构建请求体
            payload = {
                "model": self.model,
                "input": {
                    "text": text,
                    "voice": self.voice,
                    "language_type": self.language_type
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            if stream:
                headers["X-DashScope-SSE"] = "enable"
            
            logger.debug(f"🔊 TTS 请求：{text[:50]}...")
            start_time = asyncio.get_event_loop().time()
            
            async with session.post(
                self.api_url,
                json=payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ TTS API 失败：{response.status} - {error_text}")
                    return
                
                if stream:
                    # 流式处理 SSE
                    logger.debug("🔊 TTS 流式模式：开始接收 SSE 数据")
                    audio_chunk_count = 0
                    first_chunk_time = None
                    total_bytes = 0
                    async for line in response.content:
                        line_received_at = asyncio.get_event_loop().time()
                        line = line.decode('utf-8').strip()
                        if line.startswith('data:'):
                            data = line[5:].strip()
                            if data and data != '[DONE]':
                                try:
                                    import json
                                    chunk = json.loads(data)
                                    if 'output' in chunk and 'audio' in chunk['output']:
                                        audio_data = chunk['output']['audio'].get('data', '')
                                        if audio_data:
                                            audio_chunk_count += 1
                                            decoded_audio = base64.b64decode(audio_data)
                                            total_bytes += len(decoded_audio)
                                            
                                            # 记录第一个音频块的时间
                                            if first_chunk_time is None:
                                                first_chunk_time = line_received_at
                                                logger.info(f"🔊 TTS 首块延迟：{(line_received_at - start_time)*1000:.1f}ms")
                                            
                                            # 记录每个音频块的详细信息
                                            logger.debug(f"🔊 TTS 音频块 #{audio_chunk_count}: {len(decoded_audio)} bytes, 延迟 {(line_received_at - start_time)*1000:.1f}ms")
                                            
                                            yield decoded_audio
                                    else:
                                        logger.warning(f"🔊 TTS 响应格式异常：缺少 audio 字段")
                                except json.JSONDecodeError as e:
                                    logger.error(f"🔊 TTS JSON 解析失败：{e}")
                                    continue
                    
                    total_time = asyncio.get_event_loop().time() - start_time
                    avg_chunk_ms = (total_time / audio_chunk_count) * 1000 if audio_chunk_count else 0
                    logger.info(
                        f"🔊 TTS 流式完成：{audio_chunk_count} 块，{total_bytes} bytes, "
                        f"总耗时 {total_time*1000:.1f}ms, 平均 {avg_chunk_ms:.1f}ms/块"
                    )
                else:
                    # 非流式：获取完整音频 URL
                    result = await response.json()
                    if 'output' in result and 'audio' in result['output']:
                        audio_url = result['output']['audio'].get('url', '')
                        if audio_url:
                            # 下载音频
                            async with session.get(audio_url) as audio_response:
                                if audio_response.status == 200:
                                    audio_data = await audio_response.read()
                                    yield audio_data
                                else:
                                    logger.error(f"音频下载失败：{audio_response.status}")
                    else:
                        logger.error(f"TTS 响应异常：{result}")
                        
        except Exception as e:
            logger.error(f"❌ TTS 合成失败：{e}")
    
    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
    ) -> bool:
        """合成语音并保存到文件"""
        try:
            import wave
            import io
            
            audio_chunks = []
            async for chunk in self.synthesize(text, stream=False):
                audio_chunks.append(chunk)
            
            if not audio_chunks:
                logger.error("无音频数据")
                return False
            
            # 合并音频
            full_audio = b''.join(audio_chunks)
            
            # 保存为 WAV
            with wave.open(output_path, 'wb') as wav_file:
                wav_file.writeframes(full_audio)
            
            logger.info(f"✅ 音频已保存：{output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存失败：{e}")
            return False
    
    async def close(self):
        """关闭 HTTP 会话"""
        if self._session and not self._session.closed:
            await self._session.close()
