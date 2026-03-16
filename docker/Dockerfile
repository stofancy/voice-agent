# Voice Agent Plugin - Custom OpenClaw Image
FROM ghcr.io/openclaw/openclaw:latest

# 代理配置（带默认值）
# 注意：ghcr.io 和 npmjs.org 需要直连（代理不支持 HTTPS）
ARG HTTP_PROXY=http://192.168.0.147:7890
ARG HTTPS_PROXY=http://192.168.0.147:7890
ARG NO_PROXY=ghcr.io,npmjs.org,registry.npmjs.org,localhost,127.0.0.1,.local

# 打印代理配置（调试用）
RUN echo "=== Build Time Proxy Config ===" && \
    echo "HTTP_PROXY=$HTTP_PROXY" && \
    echo "HTTPS_PROXY=$HTTPS_PROXY" && \
    echo "NO_PROXY=$NO_PROXY"

# 设置构建时环境变量
ENV HTTP_PROXY=$HTTP_PROXY
ENV HTTPS_PROXY=$HTTPS_PROXY
ENV NO_PROXY=$NO_PROXY
ENV http_proxy=$HTTP_PROXY
ENV https_proxy=$HTTPS_PROXY
ENV no_proxy=$NO_PROXY

# 使用 root 用户安装插件
USER root

# 创建插件目录
RUN mkdir -p /home/node/.openclaw/extensions && \
    mkdir -p /tmp/voice-agent-src

# 复制插件源代码
COPY packages/server /tmp/voice-agent-src

# 配置 npm 代理（npm 使用小写环境变量）
WORKDIR /tmp/voice-agent-src
RUN echo "=== npm proxy config ===" && \
    echo "Using proxy: $http_proxy" && \
    echo "NO_PROXY: $no_proxy" && \
    npm config set proxy "$http_proxy" && \
    npm config set https-proxy "$https_proxy" && \
    npm config set strict-ssl false && \
    npm config set registry https://registry.npmjs.org/ && \
    echo "=== npm config list ===" && \
    npm config list

# 安装插件依赖并编译（带详细日志）
RUN echo "=== npm install start ===" && \
    echo "Proxy: $http_proxy, NO_PROXY: $no_proxy" && \
    npm install --omit=dev --loglevel verbose 2>&1 && \
    echo "=== npm build start ===" && \
    npm run build 2>&1 && \
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
