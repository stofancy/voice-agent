# STT Provider 技能

## 概述
本技能指导如何为 voice-agent 项目实现 Speech-to-Text (STT) 语音识别provider。

## 项目结构
- 基础抽象类: `src/server/stt/base.py` - `BaseSTT`
- 工厂模式: `src/server/stt/factory.py` - `create_stt()`
- 具体实现: `src/server/stt/*.py`

## 如何实现新的 STT Provider

### 1. 创建实现类
继承 `BaseSTT` 抽象类，实现以下方法:

```python
from .base import BaseSTT
from typing import Tuple
import numpy as np

class MySTT(BaseSTT):
    def __init__(self, api_key: str, base_url: str, model: str, language: str = "zh", **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.language = language
        # 初始化客户端等
        self._client = None

    async def transcribe(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
    ) -> Tuple[str, bool]:
        """
        识别音频，返回 (识别文本, 是否成功)
        """
        # 1. 将 numpy 音频转换为 API 所需格式
        # 2. 调用 STT API
        # 3. 返回识别结果
        pass

    async def close(self) -> None:
        """释放资源"""
        self._client = None
```

### 2. 音频格式转换
项目中音频使用 numpy float32 格式，采样率 16kHz。转换为 WAV:

```python
import io
import wave
import base64
import numpy as np

def _numpy_to_wav(self, audio_data: np.ndarray, sample_rate: int = 16000) -> bytes:
    if audio_data.dtype in (np.float32, np.float64):
        audio_int16 = (audio_data * 32767).astype(np.int16)
    else:
        audio_int16 = audio_data.astype(np.int16)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    return buffer.getvalue()
```

### 3. 注册到工厂
在 `src/server/stt/factory.py` 中添加:

```python
# 添加 provider 默认配置
_PROVIDER_DEFAULTS = {
    # ... 其他 providers
    "my_provider": {
        "base_url": "https://api.example.com/v1",
        "model": "my-asr-model",
    },
}

# 在 create_stt() 函数中添加分支
elif provider == "my_provider":
    from .my_stt import MySTT
    stt = MySTT(
        api_key=api_key,
        base_url=resolved_base_url,
        model=resolved_model,
        language=language,
        **kwargs,
    )
```

### 4. 使用 OpenAI 兼容 API
如果使用 OpenAI 兼容的 ASR API (如 qwen-asr, whisper):

```python
from openai import AsyncOpenAI

class OpenAICompatibleSTT(BaseSTT):
    def __init__(self, api_key: str, base_url: str, model: str, language: str = "zh", **kwargs):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.language = language

    async def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Tuple[str, bool]:
        # 转换为 WAV
        wav_data = self._numpy_to_wav(audio_data, sample_rate)
        base64_audio = base64.b64encode(wav_data).decode("utf-8")
        data_uri = f"data:audio/wav;base64,{base64_audio}"

        # 调用 API
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [{"type": "input_audio", "input_audio": {"data": data_uri}}]
            }],
            extra_body={"asr_options": {"language": self.language, "enable_itn": True}}
        )
        return response.choices[0].message.content, True
```

## 现有 STT Providers
- `bailian`: 阿里云百炼 Qwen-ASR (默认)
- `openai_compatible`: OpenAI Whisper 兼容 API
- `gemini`: Google Gemini ASR

## 环境配置
通过环境变量配置:
- `OPENCLAW_STT_PROVIDER`: provider 名称
- `OPENCLAW_STT_API_KEY`: API 密钥
- `OPENCLAW_STT_MODEL`: 模型名称
- `OPENCLAW_STT_BASE_URL`: API 地址
- `OPENCLAW_STT_LANGUAGE`: 识别语言 (默认 "zh")
