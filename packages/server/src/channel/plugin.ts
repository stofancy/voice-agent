// OpenClaw Channel Plugin 实现
import type { ChannelPlugin } from 'openclaw/plugin-sdk';
import { SessionManager } from '../session/manager.js';
import { VoiceAgentWebSocketServer } from '../websocket/server.js';

interface VoiceAgentConfig {
  enabled: boolean;
  serve: {
    port: number;
    path: string;
    bind: string;
  };
  bailian: {
    apiKey: string;
    sttModel: string;
    ttsModel: string;
    ttsVoice: string;
  };
  audio: {
    inputSampleRate: number;
    outputSampleRate: number;
  };
  session: {
    maxDurationMs: number;
    idleTimeoutMs: number;
  };
  security: {
    pairingRequired: boolean;
  };
  gateway?: {
    url?: string;
    token?: string;
  };
}

let wsServer: VoiceAgentWebSocketServer | null = null;
let sessionManager: SessionManager | null = null;

// 存储 WebSocket 连接映射（userId -> ws）
const userConnections: Map<string, WebSocket> = new Map();

export const voiceAgentPlugin: ChannelPlugin = {
  id: 'voice-agent',
  meta: {
    id: 'voice-agent',
    label: 'Voice Agent',
    selectionLabel: 'Voice Agent (Browser)',
    docsPath: '/plugins/voice-agent',
    docsLabel: 'voice-agent',
    blurb: 'Browser-based voice interaction with Bailian STT/TTS',
    order: 80,
  },

  capabilities: {
    chatTypes: ['direct'],
    media: true,
    reactions: false,
    threads: false,
    polls: false,
    nativeCommands: false,
    blockStreaming: true,
  },

  pairing: {
    idLabel: 'voiceAgentUserId',
    notifyApproval: async ({ cfg, id }) => {
      console.log(`[VoiceAgent] Pairing approved for user: ${id}`);
      // TODO: 发送配对成功通知
    },
  },

  config: {
    listAccountIds: () => ['default'],
    resolveAccount: (cfg, accountId) => {
      const config = cfg as VoiceAgentConfig;
      return {
        accountId,
        configured: !!config.bailian.apiKey,
        enabled: config.enabled,
      };
    },
    defaultAccountId: () => 'default',
    isConfigured: (account) => account.configured,
    describeAccount: (account) => ({
      accountId: account.accountId,
      enabled: account.enabled,
      configured: account.configured,
      name: 'Voice Agent',
    }),
  },

  gateway: {
    startAccount: async (ctx) => {
      const config = ctx.cfg as VoiceAgentConfig;
      
      console.log('[VoiceAgent] Starting voice agent server...');
      
      // 创建会话管理器
      sessionManager = new SessionManager({
        maxDurationMs: config.session.maxDurationMs,
        idleTimeoutMs: config.session.idleTimeoutMs,
      });

      // 创建 WebSocket 服务器
      wsServer = new VoiceAgentWebSocketServer(
        {
          port: config.serve.port,
          path: config.serve.path,
          bind: config.serve.bind,
          bailianApiKey: config.bailian.apiKey,
          sttModel: config.bailian.sttModel,
          ttsModel: config.bailian.ttsModel,
          ttsVoice: config.bailian.ttsVoice,
          gatewayUrl: config.gateway?.url,
          gatewayToken: config.gateway?.token,
        },
        sessionManager
      );

      console.log('[VoiceAgent] Voice agent server started');

      return {
        port: config.serve.port,
      };
    },

    stopAccount: async (ctx) => {
      console.log('[VoiceAgent] Stopping voice agent server...');
      
      if (wsServer) {
        wsServer.close();
        wsServer = null;
      }
      
      if (sessionManager) {
        sessionManager.destroy();
        sessionManager = null;
      }

      userConnections.clear();

      console.log('[VoiceAgent] Voice agent server stopped');
    },
  },

  messaging: {
    normalizeTarget: (raw) => {
      // 简单的目标解析
      if (!raw) return undefined;
      return String(raw);
    },
    targetResolver: {
      looksLikeId: (id) => typeof id === 'string' && id.length > 0,
      hint: '<user-id>',
    },
  },

  outbound: {
    send: async ({ to, text, cfg }) => {
      console.log(`[VoiceAgent] Send to ${to}: ${text}`);
      
      // 查找用户的 WebSocket 连接
      const ws = userConnections.get(to);
      
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.warn(`[VoiceAgent] User ${to} not connected`);
        throw new Error(`User ${to} is not connected`);
      }

      // 发送消息
      const message = {
        type: 'agent_message',
        data: {
          text,
          timestamp: Date.now(),
        },
      };

      ws.send(JSON.stringify(message));
      console.log(`[VoiceAgent] Message sent to ${to}`);

      return {
        messageId: `va_${Date.now()}`,
        timestamp: Date.now(),
      };
    },
  },
};

// 导出用于注册 WebSocket 连接的函数
export function registerUserConnection(userId: string, ws: WebSocket): void {
  userConnections.set(userId, ws);
  console.log(`[VoiceAgent] User ${userId} registered`);
}

export function unregisterUserConnection(userId: string): void {
  userConnections.delete(userId);
  console.log(`[VoiceAgent] User ${userId} unregistered`);
}
