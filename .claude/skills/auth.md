# Auth System 技能

## 概述
本技能指导如何理解和使用 voice-agent 项目的认证和 API Key 管理系统。

## 项目结构
- 认证模块: `src/server/auth.py`

## 核心组件

### 1. APIKey 数据类
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

@dataclass
class APIKey:
    key_id: str              # 内部 ID
    key_hash: str            # 密钥哈希 (安全存储)
    name: str                # 密钥名称
    created_at: datetime     # 创建时间

    # 限制
    rate_limit_per_minute: int = 60      # 每分钟请求限制
    monthly_minutes: Optional[int] = None  # 每月分钟数限制 (None=无限)

    # 使用统计
    minutes_used: float = 0.0
    last_request_at: Optional[datetime] = None
    request_count_this_minute: int = 0

    # 功能开关
    features: Dict[str, bool] = None  # 功能特性

    # 状态
    active: bool = True
    tier: str = "free"  # free, pro, enterprise
```

### 2. TokenManager
管理 API Key 的生成、验证和使用统计:

```python
class TokenManager:
    def __init__(self):
        self._keys: Dict[str, APIKey] = {}           # key_id -> APIKey
        self._key_to_id: Dict[str, str] = {}         # hash -> key_id

    def generate_key(
        self,
        name: str,
        tier: str = "free",
        rate_limit: int = 60,
        monthly_minutes: Optional[int] = None,
    ) -> tuple[str, APIKey]:
        """生成新 API Key"""
        key_id = secrets.token_hex(8)
        plaintext_key = f"ocv_{secrets.token_urlsafe(32)}"  # 前缀 ocv_
        key_hash = self._hash_key(plaintext_key)

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            created_at=datetime.now(),
            rate_limit_per_minute=rate_limit,
            monthly_minutes=monthly_minutes,
            tier=tier,
        )

        self._keys[key_id] = api_key
        self._key_to_id[key_hash] = key_id

        return plaintext_key, api_key

    def validate_key(self, plaintext_key: str) -> Optional[APIKey]:
        """验证 API Key"""
        if not plaintext_key or not plaintext_key.startswith("ocv_"):
            return None

        key_hash = self._hash_key(plaintext_key)
        key_id = self._key_to_id.get(key_hash)

        if not key_id:
            return None

        api_key = self._keys.get(key_id)

        if not api_key or not api_key.active:
            return None

        return api_key

    def check_rate_limit(self, api_key: APIKey) -> bool:
        """检查速率限制"""
        now = datetime.now()

        # 新一分钟重置计数器
        if api_key.last_request_at:
            elapsed = (now - api_key.last_request_at).total_seconds()
            if elapsed >= 60:
                api_key.request_count_this_minute = 0

        # 检查限制
        if api_key.request_count_this_minute >= api_key.rate_limit_per_minute:
            return False

        # 更新计数器
        api_key.request_count_this_minute += 1
        api_key.last_request_at = now

        return True

    def check_monthly_quota(self, api_key: APIKey, minutes: float = 0) -> bool:
        """检查月度配额"""
        if api_key.monthly_minutes is None:
            return True  # 无限
        return (api_key.minutes_used + minutes) <= api_key.monthly_minutes

    def record_usage(self, api_key: APIKey, minutes: float):
        """记录使用时长"""
        api_key.minutes_used += minutes

    def get_usage(self, api_key: APIKey) -> Dict:
        """获取使用统计"""
        return {
            "key_id": api_key.key_id,
            "name": api_key.name,
            "tier": api_key.tier,
            "minutes_used": round(api_key.minutes_used, 2),
            "monthly_limit": api_key.monthly_minutes,
            "rate_limit": api_key.rate_limit_per_minute,
            "features": api_key.features,
        }

    def _hash_key(self, plaintext_key: str) -> str:
        """哈希密钥"""
        return hashlib.sha256(plaintext_key.encode()).hexdigest()
```

## 定价层级

```python
PRICING_TIERS = {
    "free": {
        "monthly_minutes": 60,
        "rate_limit": 30,
        "price": 0,
        "features": ["continuous_mode"],
    },
    "pro": {
        "monthly_minutes": 500,
        "rate_limit": 120,
        "price": 29,
        "features": ["continuous_mode", "voice_cloning"],
    },
    "enterprise": {
        "monthly_minutes": None,  # 无限
        "rate_limit": 500,
        "price": 99,
        "features": ["continuous_mode", "voice_cloning", "priority_queue"],
    },
}
```

## 使用方法

### 1. 在 WebSocket 中验证
```python
from .auth import token_manager

async def _validate_ws_auth(websocket: WebSocket) -> Optional[APIKey]:
    api_key_str = websocket.query_params.get("api_key") or \
                  websocket.headers.get("x-api-key")

    if settings.require_auth:
        if not api_key_str:
            await websocket.close(code=4001, reason="API key required")
            return None

        api_key = token_manager.validate_key(api_key_str)
        if not api_key:
            await websocket.close(code=4002, reason="Invalid API key")
            return None

        if not token_manager.check_rate_limit(api_key):
            await websocket.close(code=4003, reason="Rate limit exceeded")
            return None

        logger.info(f"Client connected: {api_key.name} (tier={api_key.tier})")
    else:
        # 认证禁用模式
        if api_key_str:
            api_key = token_manager.validate_key(api_key_str)
        logger.info("Client connected (auth disabled)")

    return api_key
```

### 2. REST API 创建 Key
```python
@app.post("/api/keys")
async def create_api_key(
    name: str,
    tier: str = "free",
    master_key: Optional[str] = None,
):
    # 验证 master key
    if settings.require_auth:
        if not master_key and not settings.master_key:
            return {"error": "Master key required"}

        provided_key = master_key or ""
        if provided_key != settings.master_key:
            key = token_manager.validate_key(provided_key)
            if not key or key.tier != "enterprise":
                return {"error": "Invalid master key"}

    # 生成 API Key
    tier_config = PRICING_TIERS[tier]
    plaintext_key, api_key = token_manager.generate_key(
        name=name,
        tier=tier,
        rate_limit=tier_config["rate_limit"],
        monthly_minutes=tier_config["monthly_minutes"],
    )

    return {
        "api_key": plaintext_key,  # 只返回一次!
        "key_id": api_key.key_id,
        "name": api_key.name,
        "tier": api_key.tier,
        "monthly_minutes": api_key.monthly_minutes,
        "rate_limit": api_key.rate_limit_per_minute,
    }
```

### 3. 从环境变量加载 Master Key
```python
def load_keys_from_env():
    import os
    master_key = os.getenv("OPENCLAW_MASTER_KEY")
    if master_key:
        key_hash = token_manager._hash_key(master_key)
        api_key = APIKey(
            key_id="master",
            key_hash=key_hash,
            name="Master Key",
            created_at=datetime.now(),
            rate_limit_per_minute=1000,
            monthly_minutes=None,
            tier="enterprise",
        )
        api_key.features = {
            "continuous_mode": True,
            "voice_cloning": True,
            "priority_queue": True,
        }
        token_manager._keys["master"] = api_key
        token_manager._key_to_id[key_hash] = "master"
```

## 配置

### 环境变量
```bash
# 启用认证
OPENCLAW_REQUIRE_AUTH=true

# Master Key (拥有所有权限)
OPENCLAW_MASTER_KEY=your_master_key_here

# 预定义的 API Keys
OPENCLAW_API_KEY_user1=ocv_xxx
OPENCLAW_API_KEY_user2=ocv_yyy
```

### 功能特性
```python
DEFAULT_FEATURES = {
    "continuous_mode": True,      # 连续对话模式
    "voice_cloning": False,        # 声音克隆
    "priority_queue": False,       # 优先队列
}
```

## 安全性

### 密钥存储
- 只存储密钥哈希，不存储明文
- 使用 SHA-256 哈希

### 验证流程
1. 检查密钥前缀 `ocv_`
2. 验证密钥哈希
3. 检查密钥状态 (active)
4. 检查速率限制
5. 检查月度配额
