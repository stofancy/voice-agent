// TTS 客户端 - 使用 DashScope SDK 调用百炼 API
import { MultiModalConversation } from 'dashscope';

export interface TTSClientOptions {
  apiKey: string;
  baseURL?: string;
  model?: string;
  voice?: string;
}

export interface TTSResult {
  audioUrl?: string;
  audioData?: Uint8Array;
  duration?: number;
}

export class TTSClient {
  private readonly model: string;
  private readonly voice: string;
  private readonly baseURL: string;
  private readonly apiKey: string;

  constructor(options: TTSClientOptions) {
    this.model = options.model ?? 'qwen3-tts-instruct-flash';
    this.voice = options.voice ?? 'Cherry';
    this.baseURL = options.baseURL ?? 'https://dashscope.aliyuncs.com/api/v1';
    this.apiKey = options.apiKey;
  }

  /**
   * 合成语音（非流式）
   */
  async synthesize(text: string, instructions?: string): Promise<TTSResult> {
    try {
      const response = await MultiModalConversation.call({
        model: this.model,
        apiKey: this.apiKey,
        text: text,
        voice: this.voice,
        language_type: this.detectLanguage(text),
        instructions: instructions,
        optimize_instructions: !!instructions,
        stream: false,
      });

      const audioUrl = response.output?.audio?.url;
      if (!audioUrl) {
        throw new Error('No audio URL in response');
      }

      // 下载音频数据
      const audioData = await this.downloadAudio(audioUrl);

      return {
        audioUrl,
        audioData,
        duration: this.estimateDuration(text),
      };
    } catch (error) {
      console.error('[TTSClient] Synthesis failed:', error);
      throw error;
    }
  }

  /**
   * 合成语音（流式）
   */
  async *synthesizeStream(text: string, instructions?: string): AsyncGenerator<Uint8Array> {
    try {
      const response = await MultiModalConversation.call({
        model: this.model,
        apiKey: this.apiKey,
        text: text,
        voice: this.voice,
        language_type: this.detectLanguage(text),
        instructions: instructions,
        optimize_instructions: !!instructions,
        stream: true,
      });

      for await (const chunk of response) {
        if (chunk.output?.audio?.data) {
          // Base64 解码
          const binary = atob(chunk.output.audio.data);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
          }
          yield bytes;
        }
      }
    } catch (error) {
      console.error('[TTSClient] Stream synthesis failed:', error);
      throw error;
    }
  }

  /**
   * 检测文本语种
   */
  private detectLanguage(text: string): string {
    // 简单检测：包含中文字符则返回 Chinese
    const hasChinese = /[\u4e00-\u9fa5]/.test(text);
    return hasChinese ? 'Chinese' : 'English';
  }

  /**
   * 估算语音时长（毫秒）
   */
  private estimateDuration(text: string): number {
    // 中文约 4 字/秒，英文约 5 词/秒
    const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
    const englishWords = (text.match(/[a-zA-Z]+/g) || []).length;
    
    const duration = (chineseChars / 4 + englishWords / 5) * 1000;
    return Math.max(500, duration); // 至少 500ms
  }

  /**
   * 下载音频文件
   */
  private async downloadAudio(url: string): Promise<Uint8Array> {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to download audio: ${response.statusText}`);
    }
    const arrayBuffer = await response.arrayBuffer();
    return new Uint8Array(arrayBuffer);
  }
}
