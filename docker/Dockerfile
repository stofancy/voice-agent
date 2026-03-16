# Voice Agent Plugin - Custom OpenClaw Image
FROM ghcr.io/openclaw/openclaw:latest

# 使用 root 用户安装插件
USER root

# 创建插件目录
RUN mkdir -p /home/node/.openclaw/extensions && \
    mkdir -p /tmp/voice-agent-src

# 复制插件源代码
COPY packages/server /tmp/voice-agent-src

# 安装所有依赖（包括 devDependencies 用于构建）
WORKDIR /tmp/voice-agent-src
RUN echo "=== npm install (all deps) ===" && \
    npm install 2>&1 && \
    echo "=== npm build ===" && \
    npm run build 2>&1 && \
    echo "=== npm prune (remove dev) ===" && \
    npm prune --omit=dev 2>&1 && \
    echo "=== copy files ===" && \
    cp -r /tmp/voice-agent-src /home/node/.openclaw/extensions/voice-agent && \
    chown -R node:node /home/node/.openclaw/extensions/voice-agent && \
    rm -rf /tmp/voice-agent-src && \
    echo "=== build complete ==="

# 切换回 node 用户
USER node
WORKDIR /home/node

# 设置运行时环境变量
ENV ALI_BAILIAN_API_KEY=${ALI_BAILIAN_API_KEY:-}
ENV NODE_ENV=production

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:18789/__openclaw__/health || exit 1

EXPOSE 5173 8765

CMD ["openclaw", "gateway"]
