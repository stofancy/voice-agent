# Voice Agent 测试指南

## 快速测试

### 1. 启动服务器

```bash
cd ~/workspaces/voice-agent/packages/server
npm run build
npm run start
```

### 2. 运行测试脚本

```bash
cd ~/workspaces/voice-agent
node test-e2e.js
```

## 手动测试

### 使用 WebUI 测试

1. 启动服务器（如上）

2. 启动 WebUI：
```bash
cd ~/workspaces/voice-agent/packages/webui
npm run dev
```

3. 访问 http://localhost:5173

4. 点击录音按钮，说话，停止

5. 验证：
   - ✅ 看到"录音中"状态
   - ✅ 看到"处理中"状态
   - ✅ 看到 STT 字幕
   - ✅ 听到 TTS 音频回复

## 测试检查清单

### 核心功能

- [ ] WebSocket 连接成功
- [ ] 录音功能正常
- [ ] STT 识别准确
- [ ] Agent 回复合理
- [ ] TTS 播放正常
- [ ] 状态显示正确

### 错误处理

- [ ] STT 失败有重试
- [ ] TTS 失败降级显示文本
- [ ] 断线自动清理会话
- [ ] 错误消息清晰

### 性能

- [ ] 端到端延迟 < 5s
- [ ] 支持并发连接
- [ ] 内存无泄漏

## 故障排查

### WebSocket 连接失败

```bash
# 检查端口是否被占用
lsof -i :8765

# 检查服务器日志
tail -f ~/.openclaw/logs/gateway.log | grep voice-agent
```

### STT 失败

```bash
# 检查 API Key
echo $ALI_BAILIAN_API_KEY

# 测试 STT API
# 使用官方示例代码测试
```

### TTS 失败

```bash
# 测试 Python 脚本
ALI_BAILIAN_API_KEY=sk-xxx python3 packages/server/src/tts/tts-synthesize.py "测试" "qwen3-tts-instruct-flash" "Cherry" /tmp/test.wav

# 播放测试
ffplay /tmp/test.wav
```

## 性能基准

| 指标 | 目标 | 实测 |
|------|------|------|
| STT 延迟 | < 1s | - |
| Agent 延迟 | < 3s | - |
| TTS 延迟 | < 2s | - |
| 端到端延迟 | < 5s | - |

---

*最后更新：2026-03-16*
