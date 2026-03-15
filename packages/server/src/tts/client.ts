// TTS 客户端 - 使用 OpenAI 兼容模式调用百炼 API
import OpenAI from 'openai';

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
  private client: OpenAI;
  private readonly model: string;
  private readonly voice: string;

  constructor(options: TTSClientOptions) {
    this.client = new OpenAI({
      apiKey: options.apiKey,
      baseURL: options.baseURL ?? 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    });
    this.model = options.model ?? 'qwen3-tts-instruct-flash';
    this.voice = options.voice ?? 'Cherry';
  }

  /**
   * 合成语音（非流式）
   */
  async synthesize(text: string, instructions?: string): Promise<TTSResult> {
    try {
      // 使用 OpenAI 兼容 API
      const response = await this.client.audio.speech.create({
        model: this.model,
        input: text,
        voice: this.voice,
        response_format: 'pcm',
      } as any);

      // 获取音频数据
      const arrayBuffer = await response.arrayBuffer();
      const audioData = new Uint8Array(arrayBuffer);

      return {
        audioData,
      };
    } catch (error) {
      console.error('[TTS] Synthesis error:', error);
      throw error;
    }
  }

  /**
   * 检测语言
   */
  private detectLanguage(text: string): string {
    // 简单检测：包含中文字符则返回 zh
    const hasChinese = /[\u4e00-\u9fa5]/.test(text);
    return hasChinese ? 'zh' : 'en';
  }
}
