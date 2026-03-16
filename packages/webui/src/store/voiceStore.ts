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
  
  // 音频播放
  isPlaying: boolean;
  audioQueue: Uint8Array[];
  
  // Actions
  connect: (url: string) => Promise<void>;
  disconnect: () => void;
  sendAudio: (base64: string, isFinal: boolean) => void;
  setTranscript: (text: string) => void;
  setError: (error: string | null) => void;
  playAudio: (base64: string) => void;
  processAudioQueue: () => Promise<void>;
}

export const useVoiceStore = create<VoiceState>((set, get) => ({
  connectionState: 'disconnected',
  sessionId: null,
  error: null,
  sessionState: 'idle',
  transcript: '',
  isRecording: false,
  isPlaying: false,
  audioQueue: [],
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
            // 播放音频
            get().playAudio(message.data.payload);
            break;
          case 'agent_message':
            // Agent 文本消息
            console.log('[Agent] Message:', message.data.text);
            break;
          case 'error':
            set({ 
              error: `${message.error.code}: ${message.error.message}`,
              sessionState: 'idle'
            });
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

  sendAudio: (base64: string, isFinal: boolean) => {
    const { ws } = get();
    
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.error('[WebSocket] Not connected');
      return;
    }

    // 发送音频数据
    const message = {
      type: 'audio',
      data: {
        payload: base64,
        isFinal,
      },
    };

    ws.send(JSON.stringify(message));
    console.log(`[WebSocket] Audio sent (final: ${isFinal})`);

    if (!isFinal) {
      set({ isRecording: true, sessionState: 'listening' });
    }
  },

  setTranscript: (text: string) => {
    set({ transcript: text });
  },

  setError: (error: string | null) => {
    set({ error });
  },

  playAudio: (base64: string) => {
    const { audioQueue, isPlaying } = get();
    
    // 解码 Base64
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }

    // 添加到队列
    const newQueue = [...audioQueue, bytes];
    set({ audioQueue: newQueue });

    // 如果当前没有在播放，开始播放
    if (!isPlaying) {
      get().processAudioQueue();
    }
  },

  processAudioQueue: async () => {
    const { audioQueue } = get();
    
    if (audioQueue.length === 0) {
      set({ isPlaying: false, sessionState: 'idle' });
      return;
    }

    set({ isPlaying: true, sessionState: 'speaking' });

    // 取出第一个音频块
    const [first, ...rest] = audioQueue;
    set({ audioQueue: rest });

    try {
      // 播放音频
      const audioContext = new AudioContext({ sampleRate: 24000 });
      // 创建 ArrayBuffer 副本（避免 SharedArrayBuffer 类型问题）
      const arrayBuffer = first.buffer.slice(0) as ArrayBuffer;
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      
      await new Promise<void>((resolve) => {
        source.onended = () => {
          audioContext.close();
          resolve();
        };
        source.start();
      });

      // 继续播放队列
      get().processAudioQueue();
    } catch (error) {
      console.error('[Audio] Playback error:', error);
      get().processAudioQueue(); // 继续播放下一个
    }
  },
}));
