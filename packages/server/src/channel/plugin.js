// Voice Agent Channel Plugin
import { WebSocketServer } from 'ws';
import { SessionManager } from '../session/manager.js';

let sessionManager = null;
let wsServer = null;
let isRunning = false;

function getChannelConfig(cfg) {
    if (!cfg) return {};
    const channelCfg = cfg.channels?.['voice-agent'];
    if (channelCfg) return channelCfg;
    return cfg;
}

function getVoiceAgentAccountIds(cfg) {
    const channelCfg = getChannelConfig(cfg);
    const accounts = channelCfg?.accounts || {};
    return Object.keys(accounts).length > 0 ? Object.keys(accounts) : ['default'];
}

function getVoiceAgentAccount(cfg, accountId) {
    const channelCfg = getChannelConfig(cfg);
    const accounts = channelCfg?.accounts || {};
    const accountIdToUse = accountId || 'default';
    const account = accounts[accountIdToUse] || accounts['default'] || {};
    const config = account.config || channelCfg;
    const isConfigured = !!account.configured || !!config?.bailian?.apiKey;
    return {
        accountId: accountIdToUse,
        enabled: account.enabled !== false,
        configured: isConfigured,
        name: 'Voice Agent',
        config: config,
    };
}

function getDefaultVoiceAgentAccountId(cfg) {
    return 'default';
}

export const voiceAgentPlugin = {
    id: 'voice-agent',
    meta: {
        id: 'voice-agent',
        label: 'Voice Agent',
        selectionLabel: 'Voice Agent (Browser)',
        blurb: 'Browser-based voice interaction.',
        order: 100,
    },
    capabilities: { chatTypes: ['direct'], media: true },
    config: {
        listAccountIds: (cfg) => getVoiceAgentAccountIds(cfg),
        resolveAccount: (cfg, accountId) => getVoiceAgentAccount(cfg, accountId),
        defaultAccountId: (cfg) => getDefaultVoiceAgentAccountId(cfg),
        setAccountEnabled: ({ cfg, accountId, enabled }) => {
            const channelCfg = getChannelConfig(cfg);
            const accounts = channelCfg?.accounts || {};
            return { ...cfg, channels: { ...cfg?.channels, 'voice-agent': { ...channelCfg, accounts: { ...accounts, [accountId]: { ...accounts[accountId], enabled } } } } };
        },
        deleteAccount: ({ cfg, accountId }) => {
            const channelCfg = getChannelConfig(cfg);
            const accounts = channelCfg?.accounts || {};
            const { [accountId]: removed, ...rest } = accounts;
            return { ...cfg, channels: { ...cfg?.channels, 'voice-agent': { ...channelCfg, accounts: rest } } };
        },
        isConfigured: (account) => !!account?.configured,
        describeAccount: (account) => ({
            accountId: account?.accountId || 'default',
            enabled: account?.enabled !== false,
            configured: account?.configured || false,
            name: 'Voice Agent',
        }),
    },
    gateway: {
        startAccount: async (ctx) => {
            console.log('[VoiceAgent] startAccount called!');
            
            // Prevent duplicate starts
            if (isRunning && wsServer) {
                console.log('[VoiceAgent] Already running, skipping start');
                const port = wsServer.options.port;
                return { port };
            }
            
            const cfg = ctx?.cfg;
            const accountId = ctx?.accountId || 'default';
            const channelCfg = getChannelConfig(cfg);
            const account = getVoiceAgentAccount(cfg, accountId);
            
            console.log('[VoiceAgent] account.config:', JSON.stringify(account.config));
            
            if (!account.configured) {
                throw new Error('Voice Agent not configured: apiKey required');
            }
            
            const port = channelCfg?.serve?.port || 8765;
            const path = channelCfg?.serve?.path || '/voice-agent/stream';
            
            console.log('[VoiceAgent] Starting WebSocket server on port', port, 'path', path);
            
            // Start WebSocket server
            wsServer = new WebSocketServer({ port, path });
            isRunning = true;
            
            wsServer.on('listening', () => {
                console.log('[VoiceAgent] ✅ WebSocket server listening on ws://0.0.0.0:' + port + path);
            });
            
            wsServer.on('connection', (ws, req) => {
                console.log('[VoiceAgent] 📡 New WebSocket connection from', req.socket.remoteAddress);
                
                ws.on('message', (data) => {
                    console.log('[VoiceAgent] 📥 Received:', data.toString().substring(0, 200));
                    // TODO: Parse message and send to Agent
                    // For now, echo back
                    ws.send(JSON.stringify({ type: 'echo', data: data.toString() }));
                });
                
                ws.on('close', () => {
                    console.log('[VoiceAgent] 🔌 WebSocket connection closed');
                });
                
                ws.on('error', (err) => {
                    console.error('[VoiceAgent] ❌ WebSocket error:', err.message);
                });
            });
            
            wsServer.on('error', (err) => {
                console.error('[VoiceAgent] ❌ WebSocket server error:', err.message);
                isRunning = false;
            });
            
            return { port };
        },
        stopAccount: async (ctx) => {
            console.log('[VoiceAgent] stopAccount called');
            isRunning = false;
            if (wsServer) {
                wsServer.close(() => {
                    console.log('[VoiceAgent] WebSocket server closed');
                });
                wsServer = null;
            }
            if (sessionManager) {
                sessionManager.destroy();
                sessionManager = null;
            }
        },
    },
};

export default voiceAgentPlugin;
