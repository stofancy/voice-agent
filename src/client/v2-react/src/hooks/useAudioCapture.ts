import { useRef, useCallback, useEffect } from 'react';

interface UseAudioCaptureOptions {
  onAudioData: (base64Data: string) => void;
  onSilence: () => void;
  silenceThreshold?: number;
}

export function useAudioCapture({
  onAudioData,
  onSilence,
  silenceThreshold = 1500,
}: UseAudioCaptureOptions) {
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const isRecordingRef = useRef(false);
  const lastSoundTimeRef = useRef(Date.now());

  const float32ToBase64 = useCallback((float32Array: Float32Array): string => {
    const bytes = new Uint8Array(float32Array.buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }, []);

  const startRecording = useCallback(async (): Promise<boolean> => {
    if (isRecordingRef.current) return true;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      streamRef.current = stream;
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      audioContextRef.current = new AudioCtx({ sampleRate: 16000 });
      sourceRef.current = audioContextRef.current.createMediaStreamSource(stream);
      processorRef.current = audioContextRef.current.createScriptProcessor(4096, 1, 1);

      processorRef.current.onaudioprocess = (event) => {
        if (!isRecordingRef.current) return;
        
        const audioData = event.inputBuffer.getChannelData(0);
        
        // Simple energy calculation for VAD
        let energy = 0;
        for (let i = 0; i < audioData.length; i++) {
          energy += audioData[i] * audioData[i];
        }
        energy = Math.sqrt(energy / audioData.length);

        // VAD logic - simplified
        if (energy > 0.01) {
          lastSoundTimeRef.current = Date.now();
        } else if (Date.now() - lastSoundTimeRef.current > silenceThreshold) {
          onSilence();
          lastSoundTimeRef.current = Date.now();
        }

        // Send audio data
        onAudioData(float32ToBase64(audioData));
      };

      sourceRef.current.connect(processorRef.current);
      processorRef.current.connect(audioContextRef.current.destination);

      isRecordingRef.current = true;
      lastSoundTimeRef.current = Date.now();
      return true;
    } catch (error) {
      console.error('Failed to start recording:', error);
      return false;
    }
  }, [onAudioData, onSilence, silenceThreshold, float32ToBase64]);

  const stopRecording = useCallback(() => {
    if (!isRecordingRef.current) return;

    isRecordingRef.current = false;

    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopRecording();
    };
  }, [stopRecording]);

  return {
    startRecording,
    stopRecording,
    isRecording: isRecordingRef.current,
  };
}
