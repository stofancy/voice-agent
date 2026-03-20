# LLM Provider 技能

## 概述
本技能指导如何为 voice-agent 项目实现 LLM (Large Language Model) provider。

## 项目结构
- 基础抽象类: `src/server/llm/base.py` - `BaseLLM`
- 工厂模式: `src/server/llm/factory.py` - `create_llm()`
- 具体实现: `src/server/llm/*.py`

## 如何实现新的 LLM Provider

### 1. 创建实现类
继承 `BaseLLM` 抽象类，实现以下方法:

```python
from .base import BaseLLM
from typing import AsyncGenerator, List, Dict

class MyLLM(BaseLLM):
    def __init__(
        self,
        url: str = "https://api.example.com/v1",
        model: str = "my-model",
        api_key: str = None,
        system_prompt: str = None,
        **kwargs
    ):
        self.url = url
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt or "You are a helpful voice assistant."
        self.conversation_history: List[Dict] = []
        # 初始化客户端
        self._client = None

    async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        """
        流式对话，yield 文本 chunks
        """
        # 1. 添加用户消息到历史
        self.conversation_history.append({"role": "user", "content": user_message})

        # 2. 构建消息列表
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.conversation_history[-10:])  # 保留最近10条

        # 3. 调用 LLM API (流式)
        full_response = ""
        async for chunk in self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        ):
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                yield text

        # 4. 保存助手回复到历史
        self.conversation_history.append({"role": "assistant", "content": full_response})

    def clear_history(self) -> None:
        """清除对话历史"""
        self.conversation_history = []

    @property
    def model_name(self) -> str:
        """当前模型名"""
        return self.model

    async def close(self) -> None:
        """释放资源"""
        if self._http_client:
            await self._http_client.aclose()
```

### 2. 使用 httpx + OpenAI SDK
推荐使用 httpx 作为 HTTP 客户端:

```python
import httpx
from openai import AsyncOpenAI

class OpenAILLM(BaseLLM):
    def __init__(self, url: str, model: str, api_key: str, system_prompt: str = None, **kwargs):
        self.url = url
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.conversation_history = []

        # 创建 httpx 客户端 (支持 HTTP/2)
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            http2=True,
        )

        # 创建 OpenAI 客户端
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=url,
            http_client=self._http_client,
        )
```

### 3. 注册到工厂
在 `src/server/llm/factory.py` 中添加:

```python
# 添加 provider 默认配置
_PROVIDER_DEFAULTS = {
    # ... 其他 providers
    "my_provider": {
        "base_url": "https://api.example.com/v1",
        "model": "my-llm-model",
    },
}

# 在 create_llm() 函数中添加分支
if provider in ("openclaw_gateway", "bailian", "openai", "my_provider"):
    from .my_llm import MyLLM
    llm = MyLLM(
        url=resolved_base_url,
        model=resolved_model,
        api_key=api_key,
        system_prompt=system_prompt,
        **kwargs,
    )
```

### 4. 使用 WebSocket (实时对话)
对于实时性要求高的场景，可以使用 WebSocket:

```python
import websockets
import json

class RealtimeLLM(BaseLLM):
    async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        async with websockets.connect(self.ws_url) as ws:
            # 发送消息
            await ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {"type": "message", "role": "user", "content": user_message}
            }))
            await ws.send(json.dumps({"type": "response.create"}))

            # 接收流式响应
            async for message in ws:
                data = json.loads(message)
                if data.get("type") == "response.text_delta":
                    yield data.get("delta", "")
```

## 现有 LLM Providers
- `openclaw_gateway`: OpenClaw Gateway (WebSocket 实时)
- `bailian`: 阿里云百炼 Qwen (HTTP)
- `openai`: OpenAI GPT (HTTP)
- `gemini`: Google Gemini (HTTP)

## 环境配置
通过环境变量配置:
- `OPENCLAW_LLM_PROVIDER`: provider 名称
- `OPENCLAW_LLM_API_KEY`: API 密钥
- `OPENCLAW_LLM_MODEL`: 模型名称
- `OPENCLAW_LLM_BASE_URL`: API 地址

## 系统提示词
默认系统提示词 (在 main.py 中设置):
```python
system_prompt=(
    "This conversation is happening via real-time voice chat. "
    "Keep responses concise and conversational — a few sentences "
    "at most unless the topic genuinely needs depth. "
    "No markdown, bullet points, code blocks, or special formatting."
)
```
