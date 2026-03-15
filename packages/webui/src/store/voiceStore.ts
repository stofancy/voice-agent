import { create } from 'zustand';

type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';
type SessionState = 'idle' | 'listening' | 'processing' | 'speaking';

interface VoiceState {
  // 连接状态
  connectionState: ConnectionState;
  sessionId: string | null;
  error: string | null;
  
  // 会话状态
  sessionState: SessionState;
  transcript: string;
  isRecording: boolean;
  
  // WebSocket
  ws: WebSocket | null;
  
  // Actions
  connect: (url: string) => Promise<void>;
  disconnect: () => void;
  startRecording: () => void;
  stopRecording: () => void;
  setTranscript: (text: string) => void;
  setError: (error: string | null) => void;
}

export const useVoiceStore = create<VoiceState>((set, get) => ({
  connectionState: 'disconnected',
  sessionId: null,
  error: null,
  sessionState: 'idle',
  transcript: '',
  isRecording: false,
  ws: null,

  connect: async (url: string) => {
    set({ connectionState: 'connecting', error: null });

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        set({ connectionState: 'connected' });
        console.log('[WebSocket] Connected');
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('[WebSocket] Message:', message);

        switch (message.type) {
          case 'status':
            set({ 
              sessionState: message.state,
              sessionId: message.sessionId 
            });
            break;
          case 'transcript':
            set({ transcript: message.data.text });
            break;
          case 'audio_output':
            // TODO: 播放音频
            console.log('[Audio] Received audio chunk');
            break;
        }
      };

      ws.onclose = () => {
        set({ connectionState: 'disconnected', ws: null });
        console.log('[WebSocket] Disconnected');
      };

      ws.onerror = () => {
        set({ connectionState: 'error', error: 'WebSocket connection failed' });
      };

      set({ ws });
    } catch (error) {
      set({ 
        connectionState: 'error', 
        error: error instanceof Error ? error.message : 'Connection failed' 
      });
    }
  },

  disconnect: () => {
    const { ws } = get();
    if (ws) {
      ws.close();
      set({ ws: null, connectionState: 'disconnected' });
    }
  },

  startRecording: () => {
    set({ isRecording: true, sessionState: 'listening' });
    // TODO: 开始录音并发送音频
  },

  stopRecording: () => {
    set({ isRecording: false, sessionState: 'processing' });
    // TODO: 停止录音
  },

  setTranscript: (text: string) => {
    set({ transcript: text });
  },

  setError: (error: string | null) => {
    set({ error });
  },
}));
