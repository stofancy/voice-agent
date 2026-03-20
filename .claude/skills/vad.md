# VAD (Voice Activity Detection) 技能

## 概述
本技能指导如何使用和扩展 voice-agent 项目中的 Voice Activity Detection (语音活动检测) 模块。

## 项目结构
- VAD 模块: `src/server/vad.py` - `VoiceActivityDetector`

## 使用方法

### 1. 基本使用
在 main.py 中初始化和使用 VAD:

```python
from .vad import VoiceActivityDetector

# 初始化 (在 startup 事件中)
vad = VoiceActivityDetector(threshold=0.5)

# 在 WebSocket 处理中使用
elif msg_type == "audio" and connection_state == "LISTENING":
    audio_bytes = base64.b64decode(msg["data"])
    audio_np = np.frombuffer(audio_bytes, dtype=np.float32)

    # 检测语音活动
    if vad:
        has_speech = vad.is_speech(audio_np)
        await websocket.send_json({
            "type": "vad_status",
            "speech_detected": has_speech,
        })
```

### 2. 创建自定义 VAD 实现

```python
import numpy as np
from loguru import logger

class VoiceActivityDetector:
    """Voice Activity Detection."""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.model = None
        self._load_model()

    def _load_model(self):
        """加载 VAD 模型"""
        # 可以使用不同的 VAD 模型
        try:
            import torch
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
            )
            self.model = model
            self._get_speech_timestamps = utils[0]
            logger.info("✅ Silero VAD loaded")
        except Exception as e:
            logger.warning(f"VAD not available: {e}")
            self.model = None

    def is_speech(self, audio: np.ndarray, sample_rate: int = 16000) -> bool:
        """检测音频是否包含语音"""
        if self.model is None:
            return True  # 无 VAD 时默认视为有语音

        try:
            import torch
            audio_tensor = torch.from_numpy(audio).float()
            speech_prob = self.model(audio_tensor, sample_rate).item()
            return speech_prob > self.threshold
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return True

    def get_speech_timestamps(self, audio: np.ndarray, sample_rate: int = 16000):
        """获取语音时间戳"""
        if self.model is None or not hasattr(self, '_get_speech_timestamps'):
            return None

        try:
            import torch
            audio_tensor = torch.from_numpy(audio).float()
            speech_timestamps = self._get_speech_timestamps(
                audio_tensor,
                model=self.model,
                sampling_rate=sample_rate
            )
            return speech_timestamps
        except Exception as e:
            logger.error(f"VAD timestamps error: {e}")
            return None
```

## 常用 VAD 模型

### Silero VAD (当前使用)
- 优点: 高准确率、支持多种语言、易于使用
- 缺点: 需要 PyTorch

```python
import torch
model, utils = torch.hub.load(
    repo_or_dir='snakers4/silero-vad',
    model='silero_vad',
)
speech_prob = model(audio_tensor, sample_rate).item()
```

### WebRTC VAD
- 优点: 轻量级、快速
- 缺点: 需要 C 扩展

```python
import webrtcvad
vad = webrtcvad.Vad()
vad.set_mode(3)  # 0-3, 3 是最激进
is_speech = vad.is_speech(audio_bytes, sample_rate)
```

### Paperhouse VAD
- 优点: 纯 Python 实现
- 缺点: 准确率较低

```python
from paperhouse import VAD
vad = VAD()
is_speech = vad.is_speech(audio_data, sample_rate)
```

## 配置参数

### 阈值调整
```python
# 更敏感 (检测更多语音)
vad = VoiceActivityDetector(threshold=0.3)

# 不太敏感 (只检测清晰语音)
vad = VoiceActivityDetector(threshold=0.7)
```

### 音频格式要求
- 采样率: 16kHz (默认)
- 格式: numpy float32
- 声道: 单声道

## 性能优化

### 批处理
```python
def is_speech_batch(self, audio_batch: np.ndarray, sample_rate: int = 16000) -> list:
    """批量检测语音"""
    if self.model is None:
        return [True] * len(audio_batch)

    import torch
    results = []
    for audio in audio_batch:
        audio_tensor = torch.from_numpy(audio).float()
        speech_prob = self.model(audio_tensor, sample_rate).item()
        results.append(speech_prob > self.threshold)
    return results
```

### 缓存模型
```python
# 全局缓存
_vad_model = None

def get_vad_model():
    global _vad_model
    if _vad_model is None:
        import torch
        _vad_model, _ = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
        )
    return _vad_model
```
