# OpenClaw Gateway Configuration

## 🔐 敏感信息说明

此目录包含 OpenClaw Gateway 的配置文件，**包含敏感信息**。

### 文件说明

| 文件 | 说明 | 是否提交 |
|------|------|----------|
| `openclaw.json` | 实际配置文件 | ❌ 不提交（.gitignore） |
| `openclaw.json.example` | 配置模板 | ✅ 提交 |
| `README.md` | 配置说明 | ✅ 提交 |

### 首次配置步骤

1. **复制模板**
   ```bash
   cd openclaw-gateway-config
   cp openclaw.json.example openclaw.json
   ```

2. **编辑配置**
   ```bash
   # 编辑 openclaw.json，修改以下字段：
   # 1. models.providers.bailian.apiKey → 你的百炼 API Key
   # 2. gateway.auth.token → 自定义 Gateway Token
   ```

3. **获取百炼 API Key**
   - 访问：https://bailian.console.aliyun.com/
   - 创建 API Key
   - 确保开通 STT 和 TTS 服务

4. **启动 Gateway**
   ```bash
   docker compose up -d
   ```

### 环境变量方式（推荐生产环境）

也可以使用环境变量注入，避免硬编码 API Key：

```yaml
# docker-compose.yml
services:
  openclaw-gateway:
    environment:
      - OPENCLAW_BAILIAN_API_KEY=${ALI_BAILIAN_API_KEY}
```

### 安全建议

1. **不要将 `openclaw.json` 提交到 Git**
2. **生产环境使用环境变量或 Docker Secrets**
3. **定期轮换 API Key 和 Token**
4. **限制 Gateway 访问权限**
