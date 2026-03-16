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
            # 转换音频为 WAV 格式
            wav_data = self._numpy_to_wav(audio_data, sample_rate)
            base64_audio = base64.b64encode(wav_data).decode('utf-8')
            data_uri = f"data:audio/wav;base64,{base64_audio}"
            
            # 调用百炼 API
            response = await self._client.chat.completions.create(
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
            )
            
            text = response.choices[0].message.content
            logger.debug(f"🎤 STT 识别结果：{text}")
            return text, True
            
        except Exception as e:
            logger.error(f"❌ STT 识别失败：{e}")
            return f"识别失败：{str(e)}", False
    
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
