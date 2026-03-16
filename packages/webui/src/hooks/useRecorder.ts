// 录音 Hook - MediaRecorder API 封装
import { useRef, useCallback, useEffect, useState } from 'react';

export interface UseRecorderOptions {
  onAudioData?: (base64: string, isFinal: boolean) => void;
  onError?: (error: Error) => void;
  sampleRate?: number;
}

export function useRecorder(options: UseRecorderOptions = {}) {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  
  // 使用 useState 来追踪录音状态，触发重新渲染
  const [isRecording, setIsRecording] = useState(false);

  const {
    onAudioData,
    onError,
    sampleRate = 16000,
  } = options;

  // 初始化 AudioContext
  useEffect(() => {
    audioContextRef.current = new AudioContext({ sampleRate });

    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [sampleRate]);

  // 开始录音
  const startRecording = useCallback(async (): Promise<void> => {
    // 防止重复开始
    if (isRecording) {
      console.log('[Recorder] Already recording, skipping start');
      return;
    }
    
    try {
      console.log('[Recorder] Starting recording...');
      
      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1, // 单声道
          sampleRate: sampleRate,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      streamRef.current = stream;
      chunksRef.current = [];

      // 创建 MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      });

      mediaRecorderRef.current = mediaRecorder;

      // 数据可用时
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      // 录音停止时
      mediaRecorder.onstop = async () => {
        console.log('[Recorder] Processing audio...');
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        console.log(`[Recorder] Blob size: ${blob.size} bytes`);
        
        // 转换为 PCM 16kHz 16bit
        try {
          const pcmData = await blobToPCM(blob, sampleRate);
          const base64 = arrayBufferToBase64(pcmData);
          console.log(`[Recorder] PCM data length: ${pcmData.byteLength} bytes`);

          if (onAudioData) {
            onAudioData(base64, true); // isFinal=true
            console.log('[Recorder] Audio sent to WebSocket');
          }
        } catch (error) {
          console.error('[Recorder] Failed to process audio:', error);
          if (onError && error instanceof Error) {
            onError(error);
          }
        }

        // 清理
        stream.getTracks().forEach(track => track.stop());
        streamRef.current = null;
        setIsRecording(false);
      };

      // 开始录音
      mediaRecorder.start(1000); // 每秒触发一次 dataavailable
      setIsRecording(true);
      console.log('[Recorder] Recording started');
    } catch (error) {
      console.error('[Recorder] Failed to start recording:', error);
      setIsRecording(false);
      if (onError && error instanceof Error) {
        onError(error);
      }
      throw error;
    }
  }, [sampleRate, onAudioData, onError, isRecording]);

  // 停止录音
  const stopRecording = useCallback((): void => {
    console.log(`[Recorder] stopRecording called, mediaRecorder state: ${mediaRecorderRef.current?.state}`);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      console.log('[Recorder] Recording stopped');
    } else {
      console.log('[Recorder] Not recording, nothing to stop');
      setIsRecording(false);
    }
  }, []);

  // 中断录音
  const cancelRecording = useCallback((): void => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.onstop = null; // 取消 onstop 回调
      mediaRecorderRef.current.stop();
      chunksRef.current = []; // 清空音频数据

      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }

      setIsRecording(false);
      console.log('[Recorder] Recording cancelled');
    }
  }, []);

  return {
    startRecording,
    stopRecording,
    cancelRecording,
    isRecording,
  };
}

/**
 * 将 Blob 转换为 PCM 16kHz 16bit
 */
async function blobToPCM(blob: Blob, targetSampleRate: number): Promise<ArrayBuffer> {
  const arrayBuffer = await blob.arrayBuffer();
  const audioContext = new AudioContext({ sampleRate: targetSampleRate });
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

  // 获取 PCM 数据（16bit）
  const channel = audioBuffer.getChannelData(0); // 单声道
  const pcmData = new Int16Array(channel.length);

  // 浮点转 16bit 整数
  for (let i = 0; i < channel.length; i++) {
    const s = Math.max(-1, Math.min(1, channel[i]));
    pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }

  await audioContext.close();
  return pcmData.buffer;
}

/**
 * ArrayBuffer 转 Base64
 */
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}