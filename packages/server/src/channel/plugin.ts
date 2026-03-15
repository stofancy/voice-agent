// OpenClaw Channel Plugin 实现
import type { ChannelPlugin } from 'openclaw/plugin-sdk';
import { SessionManager } from '../session/manager.js';
import { VoiceAgentWebSocketServer } from '../websocket/server.js';
import { STTClient } from '../stt/client.js';
import { TTSClient } from '../tts/client.js';

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
}

let wsServer: VoiceAgentWebSocketServer | null = null;
let sessionManager: SessionManager | null = null;

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
        },
        sessionManager
      );

      // 创建 STT/TTS 客户端（用于测试）
      const sttClient = new STTClient({
        apiKey: config.bailian.apiKey,
        model: config.bailian.sttModel,
      });

      const ttsClient = new TTSClient({
        apiKey: config.bailian.apiKey,
        model: config.bailian.ttsModel,
        voice: config.bailian.ttsVoice,
      });

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
      
      // TODO: 实现消息发送逻辑
      // 这需要通过 WebSocket 推送给已连接的客户端
      
      return {
        messageId: `va_${Date.now()}`,
        timestamp: Date.now(),
      };
    },
  },
};
