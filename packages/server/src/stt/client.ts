// STT 客户端 - 使用 OpenAI 兼容模式调用百炼 API
import OpenAI from 'openai';

export interface STTClientOptions {
  apiKey: string;
  baseURL?: string;
  model?: string;
}

export interface STTResult {
  text: string;
  language?: string;
  emotion?: string;
  confidence?: number;
}

export class STTClient {
  private client: OpenAI;
  private readonly model: string;

  constructor(options: STTClientOptions) {
    this.client = new OpenAI({
      apiKey: options.apiKey,
      baseURL: options.baseURL ?? 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    });
    this.model = options.model ?? 'qwen3-asr-flash';
  }

  /**
   * 识别音频（Base64 PCM）
   */
  async transcribe(audioBase64: string): Promise<STTResult> {
    try {
      // 转换为 data URL 格式
      const dataUrl = `data:audio/pcm;base64,${audioBase64}`;
      
      const completion = await this.client.chat.completions.create({
        model: this.model,
        messages: [
          {
            role: 'user',
            content: [
              {
                type: 'input_audio',
                input_audio: {
                  data: dataUrl,
                },
              },
            ],
          },
        ],
        stream: false,
        extra_body: {
          asr_options: {
            enable_itn: true,
          },
        },
      });

      const content = completion.choices[0]?.message?.content ?? '';
      const annotations = completion.choices[0]?.message?.annotations ?? [];
      
      return {
        text: content,
        language: (annotations[0] as any)?.language,
        emotion: (annotations[0] as any)?.emotion,
        confidence: 1.0, // API 未返回置信度
      };
    } catch (error) {
      console.error('[STTClient] Transcription failed:', error);
      throw error;
    }
  }

  /**
   * 流式识别（TODO: 实现）
   */
  async *transcribeStream(audioChunks: AsyncIterable<Uint8Array>): AsyncGenerator<STTResult> {
    // TODO: 实现流式 STT
    throw new Error('Stream transcription not implemented yet');
  }
}
