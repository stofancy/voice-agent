// OpenClaw Plugin SDK 类型声明
declare module 'openclaw' {
  export interface OpenClawPluginApi {
    logger: {
      info: (msg: string) => void;
      error: (msg: string) => void;
      debug: (msg: string) => void;
      warn: (msg: string) => void;
    };
    registerChannel: (channel: any) => void;
    on: (event: string, handler: (event: any) => void) => void;
  }

  export interface ChannelPlugin {
    id: string;
    meta: {
      id: string;
      label: string;
      selectionLabel: string;
      docsPath: string;
      docsLabel: string;
      blurb: string;
      order: number;
    };
    capabilities: {
      chatTypes: string[];
      media: boolean;
      reactions: boolean;
      threads: boolean;
      polls: boolean;
      nativeCommands: boolean;
      blockStreaming: boolean;
    };
    pairing?: {
      idLabel: string;
      notifyApproval: (params: any) => Promise<void>;
    };
    config: {
      listAccountIds: () => string[];
      resolveAccount: (cfg: any, accountId: string) => any;
      defaultAccountId: () => string;
      isConfigured: (account: any) => boolean;
      describeAccount: (account: any) => any;
    };
    gateway: {
      startAccount: (ctx: any) => Promise<any>;
      stopAccount: (ctx: any) => Promise<void>;
    };
    messaging: {
      normalizeTarget: (raw: any) => string | undefined;
      targetResolver: {
        looksLikeId: (id: any) => boolean;
        hint: string;
      };
    };
    outbound: {
      send: (params: any) => Promise<any>;
    };
  }
}
