// SPDX-License-Identifier: MIT
/**
 * Handle inbound Voice Agent messages.
 * 
 * Receives WebSocket messages, processes STT (for audio),
 * and delivers to Gateway for Agent processing.
 */

import { WebSocket } from 'ws';
import type { SessionInfo, VoiceAgentConfig } from '../../types.js';
import { STTClient } from '../../stt/client.js';
import { TTSClient } from '../../tts/client.js';
import { getRuntime } from '../../index.js';
import { createVoiceAgentDispatcher } from './dispatcher.js';

/**
 * Handle audio message with STT + Agent + TTS processing.
 * 
 * @param ws - WebSocket connection
 * @param session - User session
 * @param audioChunks - Accumulated audio chunks
 * @param config - Plugin configuration
 */
export async function handleAudioMessage(
  ws: WebSocket,
  session: SessionInfo,
  audioChunks: string[],
  config: VoiceAgentConfig
): Promise<void> {
  console.log(`[handler] Processing audio from ${session.userId || 'anonymous'}, chunks=${audioChunks.length}`);
  
  // Send processing status
  sendStatus(ws, session.sessionId, 'processing');
  
  // Combine audio chunks
  const completeAudio = audioChunks.join('');
  
  // Create STT client
  const sttClient = new STTClient({
    apiKey: config.bailian.apiKey,
    model: config.bailian.sttModel,
  });
  
  try {
    // Step 1: STT - Convert audio to text
    console.log('[handler] Calling STT...');
    const sttResult = await sttClient.transcribe(completeAudio);
    console.log(`[handler] STT result: "${sttResult.text}"`);
    
    // Send transcript to browser
    sendTranscript(ws, sttResult.text, true);
    
    // Step 2: Agent - Get AI response
    console.log('[handler] Calling Agent...');
    await callAgent(ws, session, sttResult.text, config);
    
  } catch (error) {
    console.error(`[handler] Error: ${error}`);
    sendError(ws, session.sessionId, 'STT_ERROR', error instanceof Error ? error.message : 'Unknown error');
  }
}

/**
 * Call OpenClaw Agent for response.
 * 
 * @param ws - WebSocket connection
 * @param session - User session
 * @param text - User input text
 * @param config - Plugin configuration
 */
async function callAgent(
  ws: WebSocket,
  session: SessionInfo,
  text: string,
  config: VoiceAgentConfig
): Promise<void> {
  try {
    // Get runtime for Agent calls
    const runtime = getRuntime();
    
    // Create TTS client
    const ttsClient = new TTSClient({
      apiKey: config.bailian.apiKey,
      model: config.bailian.ttsModel,
      voice: config.bailian.ttsVoice,
    });
    
    // Create dispatcher for streaming Agent replies → TTS
    const { dispatcher, replyOptions, markDispatchIdle, markFullyComplete } = 
      createVoiceAgentDispatcher(ws, session.sessionId, ttsClient);
    
    // Build message context for Agent
    const messageContext = {
      from: session.userId || 'anonymous',
      to: 'voice-agent',
      text: text,
      messageId: `va_${Date.now()}`,
      channelId: 'voice-agent',
    };
    
    console.log(`[handler] Calling Agent with text: "${text.substring(0, 50)}..."`);
    
    // Call Agent with streaming response
    // Note: Using simplified call pattern - may need adjustment based on runtime API
    const result = await runtime.channel.reply.dispatchReplyFromConfig({
      ctx: messageContext as any,
      cfg: config as any,
      dispatcher: dispatcher as any,
      replyOptions: {
        ...replyOptions,
        abortSignal: new AbortController().signal,
      },
    } as any);
    
    // Wait for all messages to be sent
    await (dispatcher as any).waitForIdle();
    markFullyComplete();
    markDispatchIdle();
    
    console.log(`[handler] Agent dispatch complete`);
    
  } catch (error) {
    console.error(`[handler] Agent call failed: ${error}`);
    sendError(ws, session.sessionId, 'AGENT_ERROR', error instanceof Error ? error.message : 'Agent processing failed');
    throw error;
  }
}

/**
 * Send status update to browser.
 */
function sendStatus(ws: WebSocket, sessionId: string, state: 'idle' | 'listening' | 'processing' | 'speaking' | 'error'): void {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'status',
      state,
      sessionId,
    }));
  }
}

/**
 * Send transcript to browser.
 */
function sendTranscript(ws: WebSocket, text: string, isFinal: boolean): void {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'transcript',
      data: {
        text,
        isFinal,
      },
    }));
  }
}

/**
 * Send error to browser.
 */
function sendError(ws: WebSocket, sessionId: string, code: string, message: string): void {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'status',
      state: 'error',
      sessionId,
      error: {
        code,
        message,
      },
    }));
  }
}
