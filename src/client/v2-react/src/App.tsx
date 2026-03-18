import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Settings, 
  History, 
  MessageSquare, 
  X, 
  Volume2, 
  VolumeX,
  Sparkles
} from 'lucide-react';
import { VoiceButton } from '@/components/VoiceButton';
import { Waveform } from '@/components/Waveform';
import { ContentPanel } from '@/components/ContentPanel';
import { useVoiceInteraction } from '@/hooks/useVoiceInteraction';
import { useAudioCapture } from '@/hooks/useAudioCapture';
import { renderMarkdown } from '@/lib/markdown';
import './App.css';

// Background images for carousel
const backgroundImages = [
  'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=1920&q=80', // Paris
  'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=1920&q=80', // Tokyo
  'https://images.unsplash.com/photo-1514282401047-d79a71a590e8?w=1920&q=80', // Maldives
  'https://images.unsplash.com/photo-1476610182048-b716b8518aae?w=1920&q=80', // Iceland
];

function App() {
  const {
    voiceState,
    transcript,
    currentMessage,
    showContent,
    subtitleEnabled,
    toggleSubtitle,
    closeContent,
  } = useVoiceInteraction();

  const [currentBgIndex, setCurrentBgIndex] = useState(0);
  const [showHistory, setShowHistory] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [autoPlay, setAutoPlay] = useState(true);
  const [continuousMode, setContinuousMode] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  
  // Transcript history state
  const [transcriptHistory, setTranscriptHistory] = useState<Array<{
    role: 'user' | 'assistant';
    text: string;
    timestamp: number;
  }>>([]);
  
  // Streaming subtitle state
  const [streamingSubtitle, setStreamingSubtitle] = useState('');

  // WebSocket ref
  const wsRef = useRef<WebSocket | null>(null);
  const isAiSpeakingRef = useRef(false);
  const isRecordingRef = useRef(false);

  // Helper function to get API key from URL or localStorage
  const getApiKey = useCallback(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('api_key') || localStorage.getItem('openclaw_api_key') || '';
  }, []);

  // WebSocket URL builder
  const getWsUrl = useCallback(() => {
    const key = getApiKey();
    const path = '/v2/ws';
    
    // Use backend URL from environment variable (with fallback)
    const backendUrl = import.meta.env.VITE_BACKEND_URL || `http://${window.location.hostname}:8766`;
    const protocol = backendUrl.startsWith('https:') ? 'wss:' : 'ws:';
    const wsHost = backendUrl.replace(/^https?:\/\//, '');
    
    if (key) {
      return `${protocol}//${wsHost}${path}?api_key=${encodeURIComponent(key)}`;
    }
    return `${protocol}//${wsHost}${path}`;
  }, []);

  // Send message via WebSocket
  const sendMessage = useCallback((type: string, data?: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const msg = JSON.stringify({ type, ...data });
      console.log('[WebSocket] Sending:', type, data ? `(${JSON.stringify(data).length} bytes)` : '');
      wsRef.current.send(msg);
    } else {
      console.warn('[WebSocket] Cannot send, state:', wsRef.current?.readyState);
    }
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((msg: any) => {
    console.log('[App] Handling message type:', msg.type);
    switch (msg.type) {
      case 'transcript':
        // User transcript received - add to history
        console.log('[App] Received transcript:', msg.text);
        if (msg.text) {
          setTranscriptHistory(prev => [...prev, {
            role: 'user',
            text: msg.text,
            timestamp: Date.now(),
          }]);
        }
        break;
      case 'subtitle_chunk':
        // Streaming subtitle text - update streaming state
        if (msg.text) {
          setStreamingSubtitle(prev => prev + msg.text);
        }
        break;
      case 'audio_chunk':
        // Audio data for TTS playback - handled by audioPlayback ref
        // This will be connected to the audio playback system
        break;
      case 'tts_start':
        isAiSpeakingRef.current = true;
        break;
      case 'tts_end':
        isAiSpeakingRef.current = false;
        // Continuous Mode: automatically start next round of listening
        if (continuousMode && !isRecordingRef.current) {
          setTimeout(() => {
            startAudioCapture().then(success => {
              if (success) {
                setIsRecording(true);
                isRecordingRef.current = true;
                sendMessage('start_listening');
              }
            });
          }, 300);
        }
        break;
      case 'response_complete':
        // Response complete - finalize streaming subtitle and add to history
        if (streamingSubtitle) {
          setTranscriptHistory(prev => [...prev, {
            role: 'assistant',
            text: streamingSubtitle,
            timestamp: Date.now(),
          }]);
          setStreamingSubtitle('');
        }
        break;
      case 'interrupt_complete':
        isAiSpeakingRef.current = false;
        setStreamingSubtitle('');
        break;
      case 'audio_response':
        // Legacy format compatibility (v1 old format)
        // Play audio data and auto-start listening if continuousMode is enabled
        if (msg.data) {
          // Audio playback would be handled by a PCMPlayer or similar
          // For now, just trigger continuous mode logic
          if (continuousMode && !isRecordingRef.current) {
            setTimeout(() => {
              startAudioCapture().then(success => {
                if (success) {
                  setIsRecording(true);
                  isRecordingRef.current = true;
                  sendMessage('start_listening');
                }
              });
            }, 500);
          }
        }
        break;
      default:
        break;
    }
  }, [continuousMode, sendMessage, streamingSubtitle]);

  // Audio capture hook
  const { startRecording: startAudioCapture, stopRecording: stopAudioCapture } = useAudioCapture({
    onAudioData: (base64Data: string) => {
      console.log('[App] onAudioData called, sending audio, length:', base64Data.length);
      console.log('[App] WebSocket state:', wsRef.current?.readyState);
      sendMessage('audio', { data: base64Data });
    },
    onSilence: () => {
      console.log('[App] onSilence called');
      // VAD detected silence - auto stop in continuous mode
      if (continuousMode && isRecordingRef.current) {
        stopAudioCapture();
        setIsRecording(false);
        isRecordingRef.current = false;
        sendMessage('stop_listening');
      }
    },
    silenceThreshold: 1500,
  });

  // Wrapper functions for VoiceButton
  const handlePressStart = useCallback(async () => {
    const success = await startAudioCapture();
    if (success) {
      setIsRecording(true);
      isRecordingRef.current = true;
      sendMessage('start_listening');
    }
  }, [startAudioCapture, sendMessage]);

  const handlePressEnd = useCallback(() => {
    stopAudioCapture();
    setIsRecording(false);
    isRecordingRef.current = false;
    sendMessage('stop_listening');
    console.log('[App] Sent stop_listening, waiting for response...');
    // Don't close WebSocket - wait for transcript/response
  }, [stopAudioCapture, sendMessage]);

  // Initialize WebSocket connection
  useEffect(() => {
    const wsUrl = getWsUrl();
    console.log('[WebSocket] Connecting to:', wsUrl);
    
    const connect = () => {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('[WebSocket] Connected, state:', wsRef.current?.readyState);
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          console.log('[WebSocket] Received:', msg.type, msg.text ? `(text: ${msg.text.substring(0, 50)}...)` : '');
          handleWebSocketMessage(msg);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('[WebSocket] Closed, state:', wsRef.current?.readyState);
        // Don't auto-reconnect if we're waiting for a response
        if (isRecordingRef.current) {
          console.log('[WebSocket] Closed while recording, reconnecting...');
          setTimeout(connect, 1500);
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('[WebSocket] Closed, state:', wsRef.current?.readyState);
        setTimeout(connect, 1500);
      };
      
      wsRef.current.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };
    };

    connect();

    // Ping interval to keep connection alive
    const pingInterval = setInterval(() => {
      sendMessage('ping');
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [getWsUrl, handleWebSocketMessage, sendMessage]);

  // Background carousel
  useEffect(() => {
    if (!autoPlay) return;
    
    const interval = setInterval(() => {
      if (!showContent) {
        setCurrentBgIndex((prev) => (prev + 1) % backgroundImages.length);
      }
    }, 8000);

    return () => clearInterval(interval);
  }, [autoPlay, showContent]);

  const getStatusText = () => {
    switch (voiceState) {
      case 'listening':
        return '正在聆听...';
      case 'processing':
        return '思考中...';
      case 'speaking':
        return '正在播放';
      default:
        return '按住说话，告诉我你想去哪里';
    }
  };

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#1a1a1a]">
      {/* Background Image Carousel */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentBgIndex}
          className="absolute inset-0"
          initial={{ opacity: 0, scale: 1.1 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.5, ease: 'easeInOut' }}
        >
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: `url(${backgroundImages[currentBgIndex]})` }}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#1a1a1a] via-[#1a1a1a]/50 to-[#1a1a1a]/30" />
        </motion.div>
      </AnimatePresence>

      {/* Header */}
      <motion.header
        className="absolute top-0 left-0 right-0 z-30 flex items-center justify-between px-6 py-4"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-[#1a1a1a]" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">AI 旅行规划师</h1>
            <p className="text-xs text-white/50">Powered by Booking.com</p>
          </div>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-2">
          <IconButton
            icon={<History className="w-5 h-5" />}
            onClick={() => setShowHistory(true)}
            label="历史"
          />
          <IconButton
            icon={<Settings className="w-5 h-5" />}
            onClick={() => setShowSettings(true)}
            label="设置"
          />
        </div>
      </motion.header>

      {/* Main Content Area */}
      <div className="relative z-10 flex flex-col items-center justify-center h-full px-6">
        {/* Destination Preview (when idle) */}
        <AnimatePresence>
          {voiceState === 'idle' && !showContent && (
            <motion.div
              className="absolute inset-x-0 top-24 px-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <div className="max-w-md mx-auto">
                <p className="text-center text-white/60 text-sm mb-4">
                  热门目的地
                </p>
                <div className="flex justify-center gap-2">
                  {['巴黎', '东京', '马尔代夫', '冰岛'].map((city, index) => (
                    <motion.button
                      key={city}
                      className={`
                        px-4 py-2 rounded-full text-sm font-medium transition-all
                        ${currentBgIndex === index 
                          ? 'gradient-bg text-[#1a1a1a]' 
                          : 'bg-white/10 text-white/70 hover:bg-white/20'
                        }
                      `}
                      onClick={() => setCurrentBgIndex(index)}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      {city}
                    </motion.button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Transcript Display */}
        <AnimatePresence>
          {subtitleEnabled && (transcript || voiceState !== 'idle') && (
            <motion.div
              className="absolute top-1/3 left-0 right-0 px-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <div className="max-w-lg mx-auto text-center">
                {transcript && (
                  <p className="text-white/80 text-lg mb-2">&ldquo;{transcript}&rdquo;</p>
                )}
                <div className="flex items-center justify-center gap-2 text-white/50">
                  <Waveform state={voiceState} barCount={3} />
                  <span className="text-sm">{getStatusText()}</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Conversation History Box (transcript-box) */}
        {transcriptHistory.length > 0 && (
          <motion.div
            className="absolute top-20 left-0 right-0 px-6 overflow-y-auto max-h-[40vh]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="max-w-2xl mx-auto">
              <div className="transcript-box">
                <h3 className="text-sm font-medium text-white/50 mb-3 uppercase tracking-wider">
                  Conversation
                </h3>
                <div className="space-y-3">
                  {transcriptHistory.map((item, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className={`p-3 rounded-lg ${
                        item.role === 'user' 
                          ? 'bg-orange-500/10 border border-orange-500/20' 
                          : 'bg-blue-500/10 border border-blue-500/20'
                      }`}
                    >
                      <p className={`text-sm ${
                        item.role === 'user' ? 'text-orange-300' : 'text-blue-300'
                      }`}>
                        <strong>{item.role === 'user' ? 'You' : 'AI'}: </strong>
                        <span 
                          className={item.role === 'assistant' ? 'prose prose-invert prose-sm' : ''}
                          dangerouslySetInnerHTML={{ 
                            __html: item.role === 'assistant' ? renderMarkdown(item.text) : item.text 
                          }}
                        />
                      </p>
                    </motion.div>
                  ))}
                  {/* Streaming subtitle display */}
                  {streamingSubtitle && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20"
                    >
                      <p className="text-sm text-blue-300">
                        <strong>AI: </strong>
                        <span dangerouslySetInnerHTML={{ __html: renderMarkdown(streamingSubtitle) }} />
                      </p>
                    </motion.div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Voice Button */}
        <div className="absolute bottom-32">
          <VoiceButton
            state={isAiSpeakingRef.current ? 'speaking' : isRecording ? 'listening' : 'idle'}
            onPressStart={handlePressStart}
            onPressEnd={handlePressEnd}
          />
        </div>

        {/* Hint Text */}
        <motion.p
          className="absolute bottom-20 text-white/40 text-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          {voiceState === 'idle' ? '按住按钮开始对话' : ''}
        </motion.p>
      </div>

      {/* Content Panel */}
      <ContentPanel
        message={currentMessage}
        onClose={closeContent}
        visible={showContent}
      />

      {/* History Drawer */}
      <AnimatePresence>
        {showHistory && (
          <>
            <motion.div
              className="absolute inset-0 bg-black/60 z-40"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowHistory(false)}
            />
            <motion.div
              className="absolute right-0 top-0 bottom-0 w-80 bg-[#2d2d2d] z-50 p-6"
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white">对话历史</h2>
                <button
                  onClick={() => setShowHistory(false)}
                  className="p-2 rounded-full hover:bg-white/10 transition-colors"
                >
                  <X className="w-5 h-5 text-white/70" />
                </button>
              </div>
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-white/5">
                  <p className="text-white/60 text-sm mb-2">今天</p>
                  <p className="text-white">我想去巴黎旅行</p>
                </div>
                <div className="p-4 rounded-xl bg-white/5">
                  <p className="text-white/60 text-sm mb-2">昨天</p>
                  <p className="text-white">推荐一些海岛度假地</p>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Settings Drawer */}
      <AnimatePresence>
        {showSettings && (
          <>
            <motion.div
              className="absolute inset-0 bg-black/60 z-40"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowSettings(false)}
            />
            <motion.div
              className="absolute right-0 top-0 bottom-0 w-80 bg-[#2d2d2d] z-50 p-6"
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white">设置</h2>
                <button
                  onClick={() => setShowSettings(false)}
                  className="p-2 rounded-full hover:bg-white/10 transition-colors"
                >
                  <X className="w-5 h-5 text-white/70" />
                </button>
              </div>

              <div className="space-y-6">
                {/* Subtitle Toggle */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <MessageSquare className="w-5 h-5 text-white/60" />
                    <span className="text-white">显示字幕</span>
                  </div>
                  <button
                    onClick={toggleSubtitle}
                    className={`
                      w-12 h-6 rounded-full transition-colors relative
                      ${subtitleEnabled ? 'bg-[#d4a853]' : 'bg-white/20'}
                    `}
                  >
                    <motion.div
                      className="absolute top-1 w-4 h-4 rounded-full bg-white"
                      animate={{ left: subtitleEnabled ? '28px' : '4px' }}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  </button>
                </div>

                {/* Auto-play Toggle */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Volume2 className="w-5 h-5 text-white/60" />
                    <span className="text-white">语音播报</span>
                  </div>
                  <button
                    onClick={() => setAutoPlay(!autoPlay)}
                    className={`
                      w-12 h-6 rounded-full transition-colors relative
                      ${autoPlay ? 'bg-[#d4a853]' : 'bg-white/20'}
                    `}
                  >
                    <motion.div
                      className="absolute top-1 w-4 h-4 rounded-full bg-white"
                      animate={{ left: autoPlay ? '28px' : '4px' }}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  </button>
                </div>

                {/* Continuous Mode Toggle */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Sparkles className="w-5 h-5 text-white/60" />
                    <span className="text-white">连续对话模式</span>
                  </div>
                  <button
                    onClick={() => setContinuousMode(!continuousMode)}
                    className={`
                      w-12 h-6 rounded-full transition-colors relative
                      ${continuousMode ? 'bg-[#d4a853]' : 'bg-white/20'}
                    `}
                  >
                    <motion.div
                      className="absolute top-1 w-4 h-4 rounded-full bg-white"
                      animate={{ left: continuousMode ? '28px' : '4px' }}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  </button>
                </div>

                {/* Clear History */}
                <button className="w-full flex items-center gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors text-left">
                  <VolumeX className="w-5 h-5 text-white/60" />
                  <span className="text-white">清除历史记录</span>
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Background Indicators */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-2 z-20">
        {backgroundImages.map((_, index) => (
          <button
            key={index}
            onClick={() => setCurrentBgIndex(index)}
            className={`
              w-2 h-2 rounded-full transition-all
              ${currentBgIndex === index 
                ? 'w-6 bg-[#d4a853]' 
                : 'bg-white/30 hover:bg-white/50'
              }
            `}
          />
        ))}
      </div>
    </div>
  );
}

function IconButton({
  icon,
  onClick,
  label,
}: {
  icon: React.ReactNode;
  onClick: () => void;
  label?: string;
}) {
  return (
    <motion.button
      onClick={onClick}
      className="p-3 rounded-full bg-white/10 backdrop-blur-sm hover:bg-white/20 transition-colors text-white/70 hover:text-white"
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      title={label}
    >
      {icon}
    </motion.button>
  );
}

export default App;
