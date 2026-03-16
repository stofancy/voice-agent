# Voice Agent Plugin - Custom OpenClaw Image
FROM ghcr.io/openclaw/openclaw:latest

# 代理配置（通过 build-arg 传入）
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# 设置环境变量
ENV HTTP_PROXY=${HTTP_PROXY:-}
ENV HTTPS_PROXY=${HTTPS_PROXY:-}
ENV NO_PROXY=${NO_PROXY:-}
ENV ALI_BAILIAN_API_KEY=${ALI_BAILIAN_API_KEY:-}
ENV NODE_ENV=production

# 使用 root 用户安装插件
USER root

# 创建插件目录
RUN mkdir -p /home/node/.openclaw/extensions && \
    mkdir -p /tmp/voice-agent-src

# 复制插件源代码
COPY packages/server /tmp/voice-agent-src

# 配置 npm 代理
RUN if [ -n "$HTTP_PROXY" ]; then \
      npm config set proxy $HTTP_PROXY && \
      npm config set https-proxy $HTTPS_PROXY && \
      npm config set strict-ssl false; \
    fi

# 安装插件依赖并编译
WORKDIR /tmp/voice-agent-src
RUN npm install --omit=dev && \
    npm run build && \
    cp -r /tmp/voice-agent-src /home/node/.openclaw/extensions/voice-agent && \
    chown -R node:node /home/node/.openclaw/extensions/voice-agent && \
    rm -rf /tmp/voice-agent-src

# 切换回 node 用户
USER node
WORKDIR /home/node

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:18789/__openclaw__/health || exit 1

EXPOSE 5173 8765

CMD ["openclaw", "gateway"]
