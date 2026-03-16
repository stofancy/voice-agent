// Voice Agent Plugin Entry Point
import type { OpenClawPluginApi } from 'openclaw';
import { voiceAgentPlugin } from './channel/plugin.js';
import { VoiceAgentWebSocketServer } from './websocket/server.js';
import { SessionManager } from './session/manager.js';

// ★ Critical: Save runtime for Agent calls
let pluginRuntime: any = null;
let wsServer: VoiceAgentWebSocketServer | null = null;

export function getRuntime(): any {
  if (!pluginRuntime) {
    throw new Error('Plugin runtime not initialized - call register() first');
  }
  return pluginRuntime;
}

const plugin = {
  id: 'voice-agent',
  name: 'Voice Agent',
  description: 'Browser-based voice interaction channel with Bailian STT/TTS',
  configSchema: {
    parse(value: unknown) {
      const raw = value && typeof value === 'object' ? (value as any) : {};
      
      return {
        enabled: raw.enabled === false ? false : true,
        serve: {
          port: typeof raw.serve?.port === 'number' ? raw.serve.port : 8765,
          path: typeof raw.serve?.path === 'string' ? raw.serve.path : '/voice-agent/stream',
          bind: typeof raw.serve?.bind === 'string' ? raw.serve.bind : '0.0.0.0',
        },
        bailian: {
          apiKey: process.env.ALI_BAILIAN_API_KEY || (raw.bailian?.apiKey as string) || '',
          sttModel: (raw.bailian?.sttModel as string) || 'qwen3-asr-flash',
          ttsModel: (raw.bailian?.ttsModel as string) || 'qwen3-tts-instruct-flash',
          ttsVoice: (raw.bailian?.ttsVoice as string) || 'Cherry',
        },
        audio: {
          inputSampleRate: (raw.audio?.inputSampleRate as number) || 16000,
          outputSampleRate: (raw.audio?.outputSampleRate as number) || 24000,
        },
        session: {
          maxDurationMs: (raw.session?.maxDurationMs as number) || 300000,
          idleTimeoutMs: (raw.session?.idleTimeoutMs as number) || 30000,
        },
        security: {
          pairingRequired: raw.security?.pairingRequired !== false,
        },
      };
    },
    uiHints: {
      'serve.port': { label: 'WebSocket Port' },
      'serve.path': { label: 'WebSocket Path' },
      'bailian.apiKey': { label: 'Bailian API Key', sensitive: true },
      'bailian.sttModel': { label: 'STT Model' },
      'bailian.ttsModel': { label: 'TTS Model' },
      'bailian.ttsVoice': { label: 'TTS Voice' },
    },
  },
  register(api: OpenClawPluginApi) {
    // ★ Critical: Save runtime for Agent calls
    pluginRuntime = (api as any).runtime;
    
    // 获取配置
    const config = (api as any).config?.plugins?.['voice-agent'] || {};
    const serveConfig = config.serve || {};
    const bailianConfig = config.bailian || {};
    
    // 注册 Channel
    api.registerChannel({ plugin: voiceAgentPlugin });

    // 启动 WebSocket 服务器（构造函数中自动启动）
    const sessionManager = new SessionManager({
      maxDurationMs: config.session?.maxDurationMs || 300000,
      idleTimeoutMs: config.session?.idleTimeoutMs || 30000,
    });
    
    wsServer = new VoiceAgentWebSocketServer({
      port: serveConfig.port || 8765,
      path: serveConfig.path || '/voice-agent/stream',
      bind: serveConfig.bind || '0.0.0.0',
      bailianApiKey: bailianConfig.apiKey || process.env.ALI_BAILIAN_API_KEY || '',
      sttModel: bailianConfig.sttModel || 'qwen3-asr-flash',
      ttsModel: bailianConfig.ttsModel || 'qwen3-tts-instruct-flash',
      ttsVoice: bailianConfig.ttsVoice || 'Cherry',
    }, sessionManager);
    
    api.logger.info(`[voice-agent] WebSocket server started on port ${serveConfig.port || 8765}`);

    // 日志钩子
    api.on('before_tool_call', (event) => {
      api.logger.debug(`[voice-agent] tool call: ${event.toolName}`);
    });

    api.on('after_tool_call', (event) => {
      if (event.error) {
        api.logger.error(`[voice-agent] tool fail: ${event.toolName} - ${event.error}`);
      }
    });

    api.logger.info('[voice-agent] Plugin registered');
  },
};

export default plugin;
