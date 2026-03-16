// 会话管理器
import { randomUUID } from 'crypto';
import type { SessionInfo, SessionState } from '../types.js';

export interface SessionManagerOptions {
  maxDurationMs?: number;
  idleTimeoutMs?: number;
}

export class SessionManager {
  private sessions: Map<string, SessionInfo> = new Map();
  private readonly maxDurationMs: number;
  private readonly idleTimeoutMs: number;
  private cleanupInterval?: NodeJS.Timeout;

  constructor(options: SessionManagerOptions = {}) {
    this.maxDurationMs = options.maxDurationMs ?? 5 * 60 * 1000; // 5 分钟
    this.idleTimeoutMs = options.idleTimeoutMs ?? 30 * 1000; // 30 秒
    
    // 启动清理线程
    this.startCleanup();
  }

  /**
   * 创建新会话
   */
  createSession(userId?: string): SessionInfo {
    const sessionId = randomUUID();
    const now = Date.now();
    
    const session: SessionInfo = {
      sessionId,
      state: 'idle',
      createdAt: now,
      lastActivityAt: now,
      userId,
    };
    
    this.sessions.set(sessionId, session);
    return session;
  }

  /**
   * 获取会话
   */
  getSession(sessionId: string): SessionInfo | undefined {
    return this.sessions.get(sessionId);
  }

  /**
   * 更新会话状态
   */
  updateState(sessionId: string, state: SessionState): boolean {
    const session = this.sessions.get(sessionId);
    if (!session) {
      return false;
    }
    
    session.state = state;
    session.lastActivityAt = Date.now();
    return true;
  }

  /**
   * 更新会话活动时间
   */
  touch(sessionId: string): boolean {
    const session = this.sessions.get(sessionId);
    if (!session) {
      return false;
    }
    
    session.lastActivityAt = Date.now();
    return true;
  }

  /**
   * 删除会话
   */
  deleteSession(sessionId: string): boolean {
    return this.sessions.delete(sessionId);
  }

  /**
   * 获取所有活跃会话
   */
  getActiveSessions(): SessionInfo[] {
    return Array.from(this.sessions.values());
  }

  /**
   * 清理过期会话
   */
  private cleanupExpiredSessions(): void {
    const now = Date.now();
    
    for (const [sessionId, session] of this.sessions.entries()) {
      const age = now - session.createdAt;
      const idleTime = now - session.lastActivityAt;
      
      if (age > this.maxDurationMs || idleTime > this.idleTimeoutMs) {
        this.sessions.delete(sessionId);
        console.log(`[SessionManager] Cleaned up expired session: ${sessionId}`);
      }
    }
  }

  /**
   * 启动定期清理
   */
  private startCleanup(): void {
    this.cleanupInterval = setInterval(
      () => this.cleanupExpiredSessions(),
      Math.min(this.idleTimeoutMs, 60000) // 最多 1 分钟清理一次
    );
  }

  /**
   * 停止清理
   */
  destroy(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
    this.sessions.clear();
  }
}
