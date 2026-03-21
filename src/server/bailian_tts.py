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
            logger.warning("⚠️  ALI_BAILIAN_API_KEY not set, TTS will use mock mode")
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
            # Mock 模式
            logger.debug("Mock TTS: 无音频输出")
            return
        
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
                                                logger.info(f"🔊 TTS 首块延迟：{(line_received_at - first_chunk_time)*1000:.1f}ms")

                                            # 记录每个音频块的详细信息
                                            logger.debug(f"🔊 TTS 音频块 #{audio_chunk_count}: {len(decoded_audio)} bytes, 延迟 {(line_received_at - first_chunk_time)*1000:.1f}ms")
                                            
                                            yield decoded_audio
                                    else:
                                        logger.warning(f"🔊 TTS 响应格式异常：缺少 audio 字段")
                                except json.JSONDecodeError as e:
                                    logger.error(f"🔊 TTS JSON 解析失败：{e}")
                                    continue
                    
                    total_time = asyncio.get_event_loop().time() - first_chunk_time if first_chunk_time else 0
                    logger.info(f"🔊 TTS 流式完成：{audio_chunk_count} 块，{total_bytes} bytes, 总耗时 {total_time*1000:.1f}ms, 平均 {(total_time/audio_chunk_count)*1000:.1f}ms/块")
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

    async def synthesize_incremental(
        self,
        text_chunks: AsyncGenerator[str, None],
    ) -> AsyncGenerator[bytes, None]:
        """
        增量合成：接受文本流，边接收边合成音频流。

        内部启动两个并行任务：
        1. 消费 text_chunks，累积完整文本
        2. 当累积足够文本时，调用 TTS API 并将返回的音频流立即 yield

        Args:
            text_chunks: 异步文本块生成器（来自 LLM streaming）

        Yields:
            音频数据块
        """
        if not self.api_key:
            logger.debug("Mock TTS: 无音频输出")
            return

        text_queue: asyncio.Queue[str] = asyncio.Queue()
        audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        text_complete = False
        synthesis_started = False
        min_text_length = 5  # 至少积累几个字符才开始合成

        async def text_consumer():
            """消费文本块，累积到队列"""
            nonlocal text_complete, synthesis_started
            accumulated = ""

            async for chunk in text_chunks:
                accumulated += chunk
                await text_queue.put(chunk)

                # 当累积了足够文本且尚未开始合成时，启动合成
                if len(accumulated) >= min_text_length and not synthesis_started:
                    synthesis_started = True
                    logger.debug(f"📝 文本已积累 {len(accumulated)} 字符，启动增量合成")

            text_complete = True
            await text_queue.put("__END__")  # 发送结束信号

        async def tts_producer():
            """从队列消费文本，调用 TTS API，产出音频"""
            nonlocal synthesis_started
            buffer = ""

            while not text_complete or buffer:
                try:
                    chunk = await asyncio.wait_for(text_queue.get(), timeout=0.1)
                    if chunk == "__END__":
                        # 将 __END__ 放回队列，让 text_chunk_generator 也能看到
                        await text_queue.put("__END__")
                        break
                    buffer += chunk
                except asyncio.TimeoutError:
                    # 超时但已开始合成，发送剩余文本
                    if synthesis_started and buffer:
                        pass  # 继续循环，看是否还有更多文本
                    continue

                # 当有足够文本时调用 TTS
                if len(buffer) >= min_text_length:
                    logger.debug(f"🔊 调用 TTS（文本长度：{len(buffer)}）")
                    try:
                        async for audio_chunk in self.synthesize(buffer, stream=True):
                            await audio_queue.put(audio_chunk)
                        buffer = ""  # 清空缓冲区
                    except Exception as e:
                        logger.error(f"❌ 增量 TTS 失败：{e}")
                        break

            # 发送剩余文本的音频
            if buffer:
                logger.debug(f"🔊 发送最后文本（{len(buffer)}字符）的音频")
                try:
                    async for audio_chunk in self.synthesize(buffer, stream=True):
                        await audio_queue.put(audio_chunk)
                except Exception as e:
                    logger.error(f"❌ 最后文本 TTS 失败：{e}")

            await audio_queue.put(b"__END__")  # 发送结束信号

        # 启动两个并行任务
        consumer_task = asyncio.create_task(text_consumer())
        producer_task = asyncio.create_task(tts_producer())

        # 从 audio_queue 消费音频直到结束
        while True:
            audio_chunk = await audio_queue.get()
            if audio_chunk == b"__END__":
                break
            yield audio_chunk

        await consumer_task
        await producer_task
    
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
