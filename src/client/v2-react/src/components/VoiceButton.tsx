import { motion } from 'framer-motion';
import { Mic } from 'lucide-react';
import type { VoiceState } from '@/types';

interface VoiceButtonProps {
  state: VoiceState;
  onPressStart: () => void;
  onPressEnd: () => void;
  disabled?: boolean;
}

export function VoiceButton({ state, onPressStart, onPressEnd, disabled }: VoiceButtonProps) {
  const isListening = state === 'listening';
  const isProcessing = state === 'processing';
  const isSpeaking = state === 'speaking';
  const isActive = isListening || isProcessing || isSpeaking;
  
  const handleMouseDown = () => {
    console.log('[VoiceButton] onMouseDown');
    if (!disabled && onPressStart) onPressStart();
  };
  
  const handleMouseUp = () => {
    console.log('[VoiceButton] onMouseUp');
    if (!disabled && onPressEnd) onPressEnd();
  };
  
  const handleTouchEnd = (e: React.TouchEvent) => {
    e.preventDefault();
    console.log('[VoiceButton] onTouchEnd');
    if (!disabled && onPressEnd) onPressEnd();
  };

  return (
    <div className="relative flex items-center justify-center">
      {/* Outer Rings Animation */}
      {isListening && (
        <>
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-[#d4a853]"
            initial={{ scale: 1, opacity: 0.6 }}
            animate={{ scale: 1.6, opacity: 0 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' }}
          />
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-[#d4a853]"
            initial={{ scale: 1, opacity: 0.6 }}
            animate={{ scale: 1.6, opacity: 0 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut', delay: 0.5 }}
          />
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-[#d4a853]"
            initial={{ scale: 1, opacity: 0.6 }}
            animate={{ scale: 1.6, opacity: 0 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut', delay: 1 }}
          />
        </>
      )}

      {/* Glow Effect */}
      <motion.div
        className="absolute inset-0 rounded-full"
        animate={{
          boxShadow: isListening
            ? '0 0 60px 20px rgba(212, 168, 83, 0.5)'
            : isProcessing
            ? '0 0 40px 10px rgba(224, 122, 95, 0.3)'
            : isSpeaking
            ? '0 0 40px 10px rgba(212, 168, 83, 0.3)'
            : '0 0 20px 5px rgba(212, 168, 83, 0.2)',
        }}
        transition={{ duration: 0.3 }}
      />

      {/* Main Button */}
      <motion.button
        className={`
          relative w-20 h-20 rounded-full flex items-center justify-center
          transition-all duration-200
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        style={{
          background: isActive
            ? 'linear-gradient(135deg, #d4a853 0%, #e07a5f 100%)'
            : 'linear-gradient(135deg, rgba(212, 168, 83, 0.9) 0%, rgba(224, 122, 95, 0.9) 100%)',
        }}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={!disabled && isListening ? handleMouseUp : undefined}
        onTouchStart={handleMouseDown}
        onTouchEnd={handleTouchEnd}
        onClick={handleMouseDown}
        whileHover={!disabled ? { scale: 1.05 } : {}}
        whileTap={!disabled ? { scale: 0.95 } : {}}
        animate={{
          scale: isListening ? [1, 1.05, 1] : 1,
        }}
        transition={{
          scale: isListening
            ? { duration: 1, repeat: Infinity, ease: 'easeInOut' }
            : { duration: 0.2 },
        }}
      >
        {/* Inner Circle */}
        <div className="absolute inset-2 rounded-full bg-gradient-to-br from-[#e8c878] to-[#e08a6f] opacity-50" />
        
        {/* Icon */}
        <motion.div
          animate={{
            scale: isListening ? [1, 1.2, 1] : 1,
          }}
          transition={{
            duration: 0.5,
            repeat: isListening ? Infinity : 0,
          }}
        >
          <Mic 
            className={`w-8 h-8 ${isActive ? 'text-[#1a1a1a]' : 'text-white'}`} 
            strokeWidth={2.5}
          />
        </motion.div>
      </motion.button>

      {/* Status Indicator Dot */}
      <motion.div
        className="absolute -bottom-2 w-3 h-3 rounded-full"
        animate={{
          backgroundColor: isListening
            ? '#22c55e'
            : isProcessing
            ? '#e07a5f'
            : isSpeaking
            ? '#d4a853'
            : '#666666',
          scale: isActive ? [1, 1.2, 1] : 1,
        }}
        transition={{
          scale: { duration: 0.5, repeat: isActive ? Infinity : 0 },
        }}
      />
    </div>
  );
}
