// WebSocket 服务器 - 完整 STT→Agent→TTS 管道
import { WebSocketServer, WebSocket } from 'ws';
import type { IncomingMessage } from 'http';
import { SessionManager } from '../session/manager.js';
import type { ClientMessage, ServerMessage } from '../types.js';
import { STTClient } from '../stt/client.js';
import { TTSClient } from '../tts/client.js';
import { OpenAI } from 'openai';

export interface WebSocketServerOptions {
  port: number;
  path: string;
  bind?: string;
  bailianApiKey: string;
  sttModel: string;
  ttsModel: string;
  ttsVoice: string;
  gatewayUrl?: string;
  gatewayToken?: string;
}

interface SessionContext {
  ws: WebSocket;
  sessionId: string;
  audioChunks: string[];
  sttClient: STTClient;
  ttsClient: TTSClient;
  agentClient?: OpenAI;
}

export class VoiceAgentWebSocketServer {
  private wss: WebSocketServer;
  private sessionManager: SessionManager;
  private readonly sessions: Map<string, SessionContext> = new Map();
  private readonly port: number;
  private readonly path: string;
  private readonly gatewayUrl?: string;
  private readonly gatewayToken?: string;

  constructor(
    options: WebSocketServerOptions,
    sessionManager: SessionManager
  ) {
    this.port = options.port;
    this.path = options.path;
    this.sessionManager = sessionManager;
    this.gatewayUrl = options.gatewayUrl;
    this.gatewayToken = options.gatewayToken;

    this.wss = new WebSocketServer({
      port: options.port,
      host: options.bind ?? '0.0.0.0',
      path: options.path,
    });

    this.setupHandlers(options);
  }

  private setupHandlers(options: WebSocketServerOptions): void {
    this.wss.on('connection', (ws, request) => {
      this.handleConnection(ws, request, options);
    });

    this.wss.on('listening', () => {
      console.log(`[WebSocket] Server listening on ws://0.0.0.0:${this.port}${this.path}`);
    });

    this.wss.on('error', (error) => {
      console.error('[WebSocket] Server error:', error);
    });
  }

  private handleConnection(
    ws: WebSocket,
    request: IncomingMessage,
    options: WebSocketServerOptions
  ): void {
    // 创建会话
    const session = this.sessionManager.createSession();
    const sessionId = session.sessionId;

    // 创建会话上下文
    const context: SessionContext = {
      ws,
      sessionId,
      audioChunks: [],
      sttClient: new STTClient({
        apiKey: options.bailianApiKey,
        model: options.sttModel,
      }),
      ttsClient: new TTSClient({
        apiKey: options.bailianApiKey,
        model: options.ttsModel,
        voice: options.ttsVoice,
      }),
    };

    // 创建 Agent 客户端（如果配置了 Gateway）
    if (this.gatewayUrl && this.gatewayToken) {
      context.agentClient = new OpenAI({
        apiKey: this.gatewayToken,
        baseURL: this.gatewayUrl,
      });
    }

    this.sessions.set(sessionId, context);

    console.log(`[WebSocket] New connection: ${sessionId}`);

    // 发送会话开始消息
    this.send(ws, {
      type: 'status',
      state: 'idle',
      sessionId,
    });

    // 消息处理
    ws.on('message', (data) => {
      this.handleMessage(sessionId, data);
    });

    ws.on('close', () => {
      console.log(`[WebSocket] Connection closed: ${sessionId}`);
      this.sessions.delete(sessionId);
      this.sessionManager.deleteSession(sessionId);
    });

    ws.on('error', (error) => {
      console.error(`[WebSocket] Error on ${sessionId}:`, error);
    });

    // 心跳
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.ping();
      } else {
        clearInterval(pingInterval);
      }
    }, 30000);

    ws.on('close', () => clearInterval(pingInterval));
  }

  private async handleMessage(
    sessionId: string,
    data: any
  ): Promise<void> {
    try {
      const buffer = Buffer.isBuffer(data) ? data : Buffer.from(data as ArrayBuffer);
      const message: ClientMessage = JSON.parse(buffer.toString());
      
      // 更新会话活动
      this.sessionManager.touch(sessionId);
      const context = this.sessions.get(sessionId);
      
      if (!context) {
        console.error(`[WebSocket] Session not found: ${sessionId}`);
        return;
      }

      switch (message.type) {
        case 'audio':
          await this.handleAudio(context, message);
          break;
        case 'control':
          await this.handleControl(context, message);
          break;
        default:
          console.warn(`[WebSocket] Unknown message type: ${(message as any).type}`);
      }
    } catch (error) {
      console.error('[WebSocket] Message parse error:', error);
      const context = this.sessions.get(sessionId);
      if (context) {
        this.sendError(context.ws, sessionId, 'PARSE_ERROR', 'Invalid message format');
      }
    }
  }

  private async handleAudio(
    context: SessionContext,
    message: ClientMessage & { type: 'audio' }
  ): Promise<void> {
    const { ws, sessionId, audioChunks, sttClient, ttsClient, agentClient } = context;
    
    console.log(`[WebSocket] Audio received from ${sessionId}: ${message.data.payload.length} bytes`);

    // 累积音频块
    audioChunks.push(message.data.payload);

    // 如果是最后一个音频块（isFinal=true），开始处理
    if ((message.data as any).isFinal) {
      try {
        // 更新状态
        this.sessionManager.updateState(sessionId, 'processing');
        this.send(ws, {
          type: 'status',
          state: 'processing',
          sessionId,
        });

        // 合并所有音频块
        const fullAudio = audioChunks.join('');
        audioChunks.length = 0; // 清空

        // 1. STT: audio → text
        console.log(`[STT] Transcribing ${fullAudio.length} bytes...`);
        const sttResult = await sttClient.transcribe(fullAudio);
        console.log(`[STT] Result: ${sttResult.text}`);

        // 发送识别结果
        this.send(ws, {
          type: 'transcript',
          data: {
            text: sttResult.text,
            isFinal: true,
          },
        });

        // 2. Agent: text → reply
        let replyText = '抱歉，我暂时无法回复。';
        if (agentClient) {
          console.log(`[Agent] Sending to Agent: ${sttResult.text}`);
          const completion = await agentClient.chat.completions.create({
            model: 'gpt-4o',
            messages: [
              { role: 'user', content: sttResult.text },
            ],
          });
          replyText = completion.choices[0]?.message?.content || replyText;
          console.log(`[Agent] Reply: ${replyText}`);
        } else {
          // 如果没有配置 Agent，使用简单回复
          replyText = `我收到了："${sttResult.text}"`;
        }

        // 3. TTS: reply → audio
        console.log(`[TTS] Synthesizing: ${replyText}`);
        const ttsResult = await ttsClient.synthesize(replyText);
        
        if (ttsResult.audioData) {
          // 转换为 Base64
          const audioBase64 = Buffer.from(ttsResult.audioData).toString('base64');
          
          // 更新状态
          this.sessionManager.updateState(sessionId, 'speaking');
          this.send(ws, {
            type: 'status',
            state: 'speaking',
            sessionId,
          });

          // 发送音频
          this.send(ws, {
            type: 'audio_output',
            data: {
              format: 'pcm' as const,
              sampleRate: 24000,
              channels: 1,
              encoding: 'base64' as const,
              payload: audioBase64,
              isChunk: false,
            },
          });

          // 恢复空闲状态
          this.sessionManager.updateState(sessionId, 'idle');
          this.send(ws, {
            type: 'status',
            state: 'idle',
            sessionId,
          });
        }
      } catch (error) {
        console.error(`[Pipeline] Error:`, error);
        this.sendError(ws, sessionId, 'PIPELINE_ERROR', error instanceof Error ? error.message : 'Unknown error');
        this.sessionManager.updateState(sessionId, 'idle');
      }
    } else {
      // 中间音频块，更新状态为 listening
      this.sessionManager.updateState(sessionId, 'listening');
    }
  }

  private async handleControl(
    context: SessionContext,
    message: ClientMessage & { type: 'control' }
  ): Promise<void> {
    const { ws, sessionId, audioChunks } = context;
    
    console.log(`[WebSocket] Control message from ${sessionId}: ${message.action}`);

    switch (message.action) {
      case 'start':
        audioChunks.length = 0; // 清空之前的音频
        this.sessionManager.updateState(sessionId, 'listening');
        this.send(ws, {
          type: 'status',
          state: 'listening',
          sessionId,
        });
        break;
      case 'stop':
        this.sessionManager.updateState(sessionId, 'idle');
        this.send(ws, {
          type: 'status',
          state: 'idle',
          sessionId,
        });
        break;
      case 'interrupt':
        // 中断当前处理
        audioChunks.length = 0;
        this.sessionManager.updateState(sessionId, 'idle');
        this.send(ws, {
          type: 'status',
          state: 'idle',
          sessionId,
        });
        break;
      case 'ping':
        ws.send(JSON.stringify({ type: 'pong' }));
        break;
    }
  }

  private send(ws: WebSocket, message: ServerMessage): void {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    }
  }

  private sendError(
    ws: WebSocket,
    sessionId: string,
    code: string,
    message: string
  ): void {
    this.send(ws, {
      type: 'status',
      state: 'error',
      sessionId,
      error: { code, message },
    });
  }

  /**
   * 关闭服务器
   */
  close(): void {
    this.wss.close();
    this.sessionManager.destroy();
    this.sessions.clear();
  }
}
