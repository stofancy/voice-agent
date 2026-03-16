// WebSocket 消息类型定义

// 客户端 → 服务端
export interface AudioMessage {
  type: 'audio';
  data: {
    format: 'pcm';
    sampleRate: 16000;
    channels: 1;
    encoding: 'base64';
    payload: string;
  };
}

export interface ControlMessage {
  type: 'control';
  action: 'start' | 'stop' | 'interrupt' | 'ping';
  sessionId?: string;
}

export type ClientMessage = AudioMessage | ControlMessage;

// 服务端 → 客户端
export interface TranscriptMessage {
  type: 'transcript';
  data: {
    text: string;
    isFinal: boolean;
    confidence?: number;
    emotion?: 'neutral' | 'happy' | 'sad' | 'angry' | 'surprised' | 'fearful' | 'disgusted';
  };
}

export interface AudioOutputMessage {
  type: 'audio_output';
  data: {
    format: 'pcm';
    sampleRate: 24000;
    channels: 1;
    encoding: 'base64';
    payload: string;
    isChunk: boolean;
  };
}

export interface StatusMessage {
  type: 'status';
  state: 'listening' | 'processing' | 'speaking' | 'idle' | 'error';
  sessionId: string;
  error?: {
    code: string;
    message: string;
  };
}

export type ServerMessage = TranscriptMessage | AudioOutputMessage | StatusMessage;

// 会话状态
export type SessionState = 
  | 'idle'
  | 'listening'
  | 'processing'
  | 'responding'
  | 'speaking';

export interface SessionInfo {
  sessionId: string;
  state: SessionState;
  createdAt: number;
  lastActivityAt: number;
  userId?: string;
}

// Plugin Configuration
export interface VoiceAgentConfig {
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
