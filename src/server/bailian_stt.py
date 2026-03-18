"""
Speech-to-Text module using Alibaba Bailian (Qwen-ASR).

支持百炼 API：
- 模型：qwen3-asr-flash
- 接入方式：OpenAI 兼容 API
- URL: https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
"""

import asyncio
import base64
import os
from typing import Optional, Tuple
import numpy as np
from loguru import logger


class BailianSTT:
    """百炼语音识别（Qwen-ASR）"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen3-asr-flash",
        language: str = "zh",
    ):
        self.api_key = api_key or os.environ.get("ALI_BAILIAN_API_KEY")
        self.model = model
        self.language = language
        self._client = None
        self._setup_client()
    
    def _setup_client(self):
        """设置 OpenAI 兼容客户端"""
        if not self.api_key:
            logger.warning("⚠️  ALI_BAILIAN_API_KEY not set, STT will use mock mode")
            self._client = None
            return
        
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            logger.info(f"✅ 百炼 STT 就绪 (模型：{self.model})")
        except ImportError:
            logger.error("❌ openai package not installed")
            self._client = None
        except Exception as e:
            logger.error(f"❌ 百炼 STT 初始化失败：{e}")
            self._client = None
    
    async def transcribe(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
    ) -> Tuple[str, bool]:
        """
        识别音频
        
        Args:
            audio_data: PCM 音频数据 (numpy array, float32)
            sample_rate: 采样率 (默认 16kHz)
        
        Returns:
            (识别文本，是否成功)
        """
        if self._client is None:
            return "Mock: 语音识别服务未配置", False
        
        try:
            # 重采样到 16kHz（如果前端不是 16kHz）
            if sample_rate != 16000:
                # Use scipy for resampling (librosa not always installed)
                try:
                    from scipy import signal
                    num_samples = int(len(audio_data) * 16000 / sample_rate)
                    audio_data = signal.resample(audio_data, num_samples)
                except ImportError:
                    # Fallback: simple nearest-neighbor resampling
                    ratio = 16000 / sample_rate
                    audio_data = audio_data[::int(1/ratio)] if ratio < 1 else np.repeat(audio_data, int(ratio))
                sample_rate = 16000
                logger.debug(f"🔄 重采样到 16kHz (原始：{sample_rate}Hz)")
            
            # 转换音频为 WAV 格式
            wav_data = self._numpy_to_wav(audio_data, sample_rate)
            base64_audio = base64.b64encode(wav_data).decode('utf-8')
            data_uri = f"data:audio/wav;base64,{base64_audio}"
            
            logger.debug(f"📤 发送 STT 请求，音频长度：{len(audio_data)} samples, {len(audio_data)/16000:.2f}s")
            
            # 调用百炼 API（带超时）
            import asyncio
            try:
                response = await asyncio.wait_for(
                    self._client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_audio",
                                        "input_audio": {
                                            "data": data_uri
                                        }
                                    }
                                ]
                            }
                        ],
                        extra_body={
                            "asr_options": {
                                "language": self.language,
                                "enable_itn": True  # 逆文本标准化
                            }
                        }
                    ),
                    timeout=30.0  # 30 秒超时
                )
            except asyncio.TimeoutError:
                logger.error("❌ STT 请求超时（30 秒）")
                return "识别超时，请重试", False
            
            text = response.choices[0].message.content
            logger.info(f"🎤 STT 识别结果（原始）：{text}")
            
            # 后处理：去除重复文字（Bailian STT 流式识别已知问题）
            text = self._remove_duplicate_chars(text)
            logger.info(f"🎤 STT 识别结果（处理后）：{text}")
            return text, True
            
        except Exception as e:
            logger.error(f"❌ STT 识别失败：{type(e).__name__}: {e}")
            return f"识别失败：{str(e)}", False
    
    def _remove_duplicate_chars(self, text: str) -> str:
        """
        去除重复字符和词组（Bailian STT 流式识别修复）
        
        例如：
        - "很很多人" → "很多人"
        - "没有没有正式" → "没有正式"
        - "所以所以" → "所以"
        - "名字字" → "名字"
        """
        if not text:
            return text
        
        # 第一步：去除连续重复字符（单字重复）
        result = []
        i = 0
        while i < len(text):
            char = text[i]
            
            # 检查是否有连续重复（2-4 次）
            repeat_count = 1
            while i + repeat_count < len(text) and text[i + repeat_count] == char and repeat_count < 4:
                repeat_count += 1
            
            # 只保留一个字符
            result.append(char)
            i += repeat_count
        
        # 第二步：去除重复词组（2-4 字词组）
        text = ''.join(result)
        result = []
        i = 0
        while i < len(text):
            matched = False
            
            # 检查 2-4 字符词组的重复
            for word_len in range(2, 5):
                if i + word_len * 2 <= len(text):
                    word1 = text[i:i + word_len]
                    word2 = text[i + word_len:i + word_len * 2]
                    if word1 == word2 and word1.strip() and len(word1.strip()) >= 2:
                        result.append(word1)
                        i += word_len * 2
                        matched = True
                        break
            
            if not matched:
                result.append(text[i])
                i += 1
        
        return ''.join(result)
    
    def _numpy_to_wav(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
    ) -> bytes:
        """转换 numpy array 为 WAV 格式"""
        import io
        import wave
        
        # 归一化到 16-bit
        if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
            audio_int16 = (audio_data * 32767).astype(np.int16)
        else:
            audio_int16 = audio_data.astype(np.int16)
        
        # 创建 WAV 文件
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        return buffer.getvalue()
    
    async def transcribe_file(self, file_path: str) -> Tuple[str, bool]:
        """识别音频文件"""
        try:
            import soundfile as sf
            audio_data, sample_rate = sf.read(file_path)
            return await self.transcribe(audio_data, sample_rate)
        except Exception as e:
            logger.error(f"文件识别失败：{e}")
            return f"文件读取失败：{str(e)}", False
