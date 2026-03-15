// WebSocket 服务器
import { WebSocketServer, WebSocket } from 'ws';
import type { IncomingMessage } from 'http';
import { SessionManager } from '../session/manager.js';
import type { ClientMessage, ServerMessage } from '../types.js';

export interface WebSocketServerOptions {
  port: number;
  path: string;
  bind?: string;
}

export class VoiceAgentWebSocketServer {
  private wss: WebSocketServer;
  private sessionManager: SessionManager;
  private readonly port: number;
  private readonly path: string;

  constructor(
    options: WebSocketServerOptions,
    sessionManager: SessionManager
  ) {
    this.port = options.port;
    this.path = options.path;
    this.sessionManager = sessionManager;

    this.wss = new WebSocketServer({
      port: options.port,
      host: options.bind ?? '0.0.0.0',
      path: options.path,
    });

    this.setupHandlers();
  }

  private setupHandlers(): void {
    this.wss.on('connection', (ws, request) => {
      this.handleConnection(ws, request);
    });

    this.wss.on('listening', () => {
      console.log(`[WebSocket] Server listening on ws://0.0.0.0:${this.port}${this.path}`);
    });

    this.wss.on('error', (error) => {
      console.error('[WebSocket] Server error:', error);
    });
  }

  private handleConnection(ws: WebSocket, request: IncomingMessage): void {
    // 创建会话
    const session = this.sessionManager.createSession();
    console.log(`[WebSocket] New connection: ${session.sessionId}`);

    // 发送会话开始消息
    this.send(ws, {
      type: 'status',
      state: 'idle',
      sessionId: session.sessionId,
    });

    // 消息处理
    ws.on('message', (data) => {
      this.handleMessage(ws, session.sessionId, data);
    });

    ws.on('close', () => {
      console.log(`[WebSocket] Connection closed: ${session.sessionId}`);
      this.sessionManager.deleteSession(session.sessionId);
    });

    ws.on('error', (error) => {
      console.error(`[WebSocket] Error on ${session.sessionId}:`, error);
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

  private handleMessage(
    ws: WebSocket,
    sessionId: string,
    data: Buffer
  ): void {
    try {
      const message: ClientMessage = JSON.parse(data.toString());
      
      // 更新会话活动
      this.sessionManager.touch(sessionId);

      switch (message.type) {
        case 'audio':
          this.handleAudio(ws, sessionId, message);
          break;
        case 'control':
          this.handleControl(ws, sessionId, message);
          break;
        default:
          console.warn(`[WebSocket] Unknown message type: ${(message as any).type}`);
      }
    } catch (error) {
      console.error('[WebSocket] Message parse error:', error);
      this.sendError(ws, sessionId, 'PARSE_ERROR', 'Invalid message format');
    }
  }

  private handleAudio(
    ws: WebSocket,
    sessionId: string,
    message: ClientMessage & { type: 'audio' }
  ): void {
    // TODO: 实现音频处理逻辑
    console.log(`[WebSocket] Audio received from ${sessionId}: ${message.data.payload.length} bytes`);
    
    // 更新状态
    this.sessionManager.updateState(sessionId, 'listening');
  }

  private handleControl(
    ws: WebSocket,
    sessionId: string,
    message: ClientMessage & { type: 'control' }
  ): void {
    console.log(`[WebSocket] Control message from ${sessionId}: ${message.action}`);

    switch (message.action) {
      case 'start':
        this.sessionManager.updateState(sessionId, 'listening');
        break;
      case 'stop':
        this.sessionManager.updateState(sessionId, 'idle');
        break;
      case 'interrupt':
        // TODO: 中断当前处理
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
  }
}
