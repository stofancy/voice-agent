import { useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useVoiceStore } from './store/voiceStore';
import { useRecorder } from './hooks/useRecorder';

function App() {
  const {
    connectionState,
    sessionState,
    transcript,
    error,
    connect,
    disconnect,
    sendAudio,
    setError,
  } = useVoiceStore();

  // 录音回调
  const handleAudioData = useCallback((base64: string, isFinal: boolean) => {
    sendAudio(base64, isFinal);
  }, [sendAudio]);

  const handleError = useCallback((error: Error) => {
    setError(`录音失败：${error.message}`);
  }, [setError]);

  // 使用录音 Hook
  const {
    startRecording,
    stopRecording,
    isRecording,
  } = useRecorder({
    onAudioData: handleAudioData,
    onError: handleError,
    sampleRate: 16000,
  });

  useEffect(() => {
    // 自动连接到本地 WebSocket 服务器
    connect('ws://localhost:8765/voice-agent/stream');
    
    return () => {
      disconnect();
    };
  }, []);

  const handleRecordToggle = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const getStateText = () => {
    switch (sessionState) {
      case 'listening': return '正在听...';
      case 'processing': return '处理中...';
      case 'speaking': return '正在说话...';
      default: return '点击说话';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center p-4">
      {/* 主卡片 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md bg-white rounded-2xl shadow-xl p-6 md:p-8"
      >
        {/* 标题 */}
        <h1 className="text-2xl md:text-3xl font-bold text-center text-gray-800 mb-2">
          Voice Agent
        </h1>
        <p className="text-center text-gray-500 text-sm mb-6">
          智能语音助手
        </p>

        {/* 连接状态 */}
        <div className="flex items-center justify-center mb-4">
          <div className={`w-2 h-2 rounded-full mr-2 ${
            connectionState === 'connected' ? 'bg-green-500' :
            connectionState === 'error' ? 'bg-red-500' :
            'bg-yellow-500'
          }`} />
          <span className="text-xs text-gray-500">
            {connectionState === 'connected' ? '已连接' :
             connectionState === 'error' ? '连接失败' :
             '连接中...'}
          </span>
        </div>

        {/* 波形可视化区域 */}
        <div className="h-32 bg-gray-50 rounded-xl mb-6 flex items-center justify-center overflow-hidden">
          <AnimatePresence>
            {isRecording ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-1"
              >
                {[...Array(20)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="w-1 bg-indigo-500 rounded-full"
                    animate={{
                      height: [8, 32 + Math.random() * 32, 8],
                    }}
                    transition={{
                      duration: 0.5,
                      repeat: Infinity,
                      delay: i * 0.05,
                    }}
                  />
                ))}
              </motion.div>
            ) : (
              <div className="text-gray-400 text-sm">
                {sessionState === 'idle' ? '点击麦克风开始说话' : getStateText()}
              </div>
            )}
          </AnimatePresence>
        </div>

        {/* 实时字幕 */}
        {transcript && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 bg-indigo-50 rounded-lg"
          >
            <p className="text-gray-700 text-sm">{transcript}</p>
          </motion.div>
        )}

        {/* 录音按钮 */}
        <div className="flex justify-center mb-4">
          <motion.button
            onClick={handleRecordToggle}
            disabled={connectionState !== 'connected'}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={`w-20 h-20 rounded-full flex items-center justify-center shadow-lg ${
              isRecording
                ? 'bg-red-500 hover:bg-red-600'
                : 'bg-indigo-500 hover:bg-indigo-600'
            } ${connectionState !== 'connected' ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <svg
              className="w-8 h-8 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          </motion.button>
        </div>

        {/* 状态文字 */}
        <p className="text-center text-gray-600 text-sm">
          {getStateText()}
        </p>

        {/* 错误提示 */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg"
          >
            <p className="text-red-600 text-sm">{error}</p>
          </motion.div>
        )}
      </motion.div>

      {/* 页脚 */}
      <p className="mt-8 text-gray-400 text-xs">
        Powered by OpenClaw & Bailian
      </p>
    </div>
  );
}

export default App;
