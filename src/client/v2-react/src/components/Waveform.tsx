import { motion } from 'framer-motion';
import type { VoiceState } from '@/types';

interface WaveformProps {
  state: VoiceState;
  barCount?: number;
}

export function Waveform({ state, barCount = 5 }: WaveformProps) {
  const isListening = state === 'listening';
  const isProcessing = state === 'processing';
  const isSpeaking = state === 'speaking';
  const isActive = isListening || isProcessing || isSpeaking;

  const bars = Array.from({ length: barCount }, (_, i) => i);

  const getBarHeight = (index: number) => {
    if (isListening) {
      // Dynamic heights for listening state
      const heights = [60, 100, 80, 100, 60];
      return heights[index % heights.length];
    } else if (isProcessing) {
      // Gentle wave for processing
      return 40;
    } else if (isSpeaking) {
      // Active pattern for speaking
      const heights = [80, 60, 90, 60, 80];
      return heights[index % heights.length];
    }
    return 20;
  };

  const getAnimationDuration = () => {
    if (isListening) return 0.4;
    if (isProcessing) return 1;
    if (isSpeaking) return 0.3;
    return 1;
  };

  return (
    <div className="flex items-center justify-center gap-1.5 h-16">
      {bars.map((index) => (
        <motion.div
          key={index}
          className="w-1.5 rounded-full"
          style={{
            background: isActive
              ? 'linear-gradient(to top, #d4a853, #e07a5f)'
              : 'linear-gradient(to top, rgba(212, 168, 83, 0.3), rgba(224, 122, 95, 0.3))',
          }}
          initial={{ height: 8 }}
          animate={{
            height: isActive ? [16, getBarHeight(index), 16] : 8,
            opacity: isActive ? 1 : 0.4,
          }}
          transition={{
            height: {
              duration: getAnimationDuration(),
              repeat: Infinity,
              repeatType: 'reverse',
              ease: 'easeInOut',
              delay: index * 0.1,
            },
            opacity: { duration: 0.3 },
          }}
        />
      ))}
    </div>
  );
}

// Compact version for smaller spaces
export function WaveformCompact({ state }: WaveformProps) {
  const isActive = state !== 'idle';

  return (
    <div className="flex items-center gap-0.5">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-0.5 rounded-full bg-gradient-to-t from-[#d4a853] to-[#e07a5f]"
          animate={{
            height: isActive ? [4, 12, 4] : 4,
            opacity: isActive ? 1 : 0.5,
          }}
          transition={{
            duration: 0.5,
            repeat: Infinity,
            delay: i * 0.15,
          }}
        />
      ))}
    </div>
  );
}
