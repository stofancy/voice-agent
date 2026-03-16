// SPDX-License-Identifier: MIT
/**
 * Voice Agent Dispatcher
 * 
 * Receives streaming Agent replies and converts them to TTS audio.
 * 
 * Flow:
 * 1. Agent streams text response (chunk by chunk)
 * 2. Dispatcher receives each chunk
 * 3. Calls TTS to synthesize audio
 * 4. Sends audio to browser via WebSocket
 * 
 * Reference: HANDOVER.md Task 1, REQUIREMENTS-ANALYSIS.md Section 5.2
 */

import { WebSocket } from 'ws';
import { TTSClient } from '../../tts/client.js';

/**
 * Dispatcher state tracking.
 */
interface DispatcherState {
  isIdle: boolean;
  isFullyComplete: boolean;
  messageCount: number;
}

/**
 * Agent reply structure (from OpenClaw runtime).
 */
export interface AgentReply {
  /** Final reply (complete message). */
  final?: boolean;
  
  /** Text content (may be partial for streaming). */
  text?: string;
  
  /** Message ID (if available). */
  messageId?: string;
}

/**
 * Reply options for dispatchReplyFromConfig.
 */
export interface ReplyOptions {
  /** Abort signal for cancellation. */
  abortSignal?: AbortSignal;
  
  /** Whether to enable streaming. */
  stream?: boolean;
}

/**
 * Dispatcher result - returned from createVoiceAgentDispatcher.
 */
export interface DispatcherResult {
  /**
   * Dispatcher callback - receives Agent reply chunks.
   */
  dispatcher: (reply: AgentReply) => Promise<void>;
  
  /**
   * Reply options for dispatchReplyFromConfig.
   */
  replyOptions: ReplyOptions;
  
  /**
   * Mark dispatcher as idle (no more pending messages).
   */
  markDispatchIdle: () => void;
  
  /**
   * Mark dispatch as fully complete (all processing done).
   */
  markFullyComplete: () => void;
  
  /**
   * Wait until dispatcher is idle.
   */
  waitForIdle: () => Promise<void>;
  
  /**
   * Get current state.
   */
  getState: () => DispatcherState;
}

/**
 * Create Voice Agent Dispatcher.
 * 
 * The dispatcher receives Agent reply chunks and:
 * 1. Sends text to browser (for subtitle display)
 * 2. Calls TTS to synthesize audio
 * 3. Sends audio to browser
 * 
 * @param ws - WebSocket connection to browser
 * @param sessionId - Session ID for state tracking
 * @param ttsClient - TTS client for audio synthesis
 * @returns Dispatcher result with callback and utilities
 */
export function createVoiceAgentDispatcher(
  ws: WebSocket,
  sessionId: string,
  ttsClient: TTSClient
): DispatcherResult {
  const state: DispatcherState = {
    isIdle: true,
    isFullyComplete: false,
    messageCount: 0,
  };
  
  /**
   * Send status update to browser.
   */
  const sendStatus = (state: 'speaking' | 'idle' | 'error'): void => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'status',
        state,
        sessionId,
      }));
    }
  };
  
  /**
   * Send text to browser (for subtitle display).
   */
  const sendText = (text: string, isFinal: boolean): void => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'agent_text',
        data: {
          text,
          isFinal,
          timestamp: Date.now(),
        },
      }));
    }
  };
  
  /**
   * Send audio to browser.
   */
  const sendAudio = (audioData: Uint8Array, isChunk: boolean): void => {
    if (ws.readyState === WebSocket.OPEN) {
      const base64 = Buffer.from(audioData).toString('base64');
      ws.send(JSON.stringify({
        type: 'agent_audio',
        data: {
          audio: base64,
          isChunk,
          timestamp: Date.now(),
        },
      }));
    }
  };
  
  /**
   * Dispatcher callback - receives Agent reply chunks.
   */
  const dispatcher = async (reply: AgentReply): Promise<void> => {
    state.isIdle = false;
    state.messageCount++;
    
    const { final = false, text, messageId } = reply;
    
    console.log(`[dispatcher] Received: textLength=${text?.length ?? 0}, final=${final}`);
    
    try {
      // Step 1: Send text to browser (for subtitle display)
      if (text) {
        sendText(text, final);
        console.log(`[dispatcher] Sent text to browser (final=${final})`);
      }
      
      // Step 2: Call TTS to synthesize audio (only if text is provided)
      if (text && text.trim()) {
        console.log(`[dispatcher] Calling TTS for text: "${text.substring(0, 50)}..."`);
        
        // Update status to "speaking"
        sendStatus('speaking');
        
        try {
          // Synthesize audio
          const ttsResult = await ttsClient.synthesize(text);
          
          if (!ttsResult.audioData) {
            throw new Error('TTS returned no audio data');
          }
          
          // Send audio to browser
          sendAudio(ttsResult.audioData, !final);
          console.log(`[dispatcher] Sent audio to browser (size=${ttsResult.audioData.length} bytes)`);
        } catch (ttsError) {
          // TTS 失败降级：只发送文本，不播放音频
          console.error(`[dispatcher] TTS failed, falling back to text only: ${ttsError}`);
          
          // 发送错误通知但不中断流程
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: 'error',
              data: {
                code: 'TTS_FALLBACK',
                message: 'TTS failed, showing text only',
              },
            }));
          }
        }
      }
      
      // Step 3: Mark as complete if this is the final chunk
      if (final) {
        state.isFullyComplete = true;
        sendStatus('idle');
        console.log(`[dispatcher] Final chunk received, dispatch complete (messages=${state.messageCount})`);
      }
    } catch (error) {
      console.error(`[dispatcher] Error: ${error}`);
      
      // Send error to browser
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'error',
          data: {
            code: 'TTS_ERROR',
            message: 'Audio synthesis failed',
          },
        }));
      }
      
      // Re-throw to propagate error
      throw error;
    }
  };
  
  /**
   * Reply options for dispatchReplyFromConfig.
   */
  const replyOptions: ReplyOptions = {
    stream: true,  // Enable streaming for real-time TTS
  };
  
  /**
   * Mark dispatcher as idle.
   */
  const markDispatchIdle = (): void => {
    state.isIdle = true;
    console.log('[dispatcher] Marked as idle');
  };
  
  /**
   * Mark dispatch as fully complete.
   */
  const markFullyComplete = (): void => {
    state.isFullyComplete = true;
    console.log('[dispatcher] Marked as fully complete');
  };
  
  /**
   * Wait until dispatcher is idle.
   */
  const waitForIdle = async (): Promise<void> => {
    while (!state.isIdle) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    console.log('[dispatcher] Waited until idle');
  };
  
  /**
   * Get current state.
   */
  const getState = (): DispatcherState => ({ ...state });
  
  return {
    dispatcher,
    replyOptions,
    markDispatchIdle,
    markFullyComplete,
    waitForIdle,
    getState,
  };
}

export default createVoiceAgentDispatcher;
