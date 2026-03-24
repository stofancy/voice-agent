(function () {
    const talkBtnEl = document.getElementById('talkBtn');
    const interruptBtnEl = document.getElementById('interruptBtn');
    const clearHistoryBtnEl = document.getElementById('clearHistoryBtn');
    const continuousModeBtnEl = document.getElementById('continuousModeBtn');

    const talkButton = new window.TalkButton(talkBtnEl);
    const ui = new window.UIController();

    let interruptButton;
    let ws = null;
    let isRecording = false;
    let stream = null;
    let audioContext = null;
    let processor = null;
    let source = null;
    let assistantStreamingText = '';
    let assistantStreamingMessageEl = null;
    let isAiSpeaking = false;
    let ttsEndReceived = false;
    let touchHandled = false;
    let toolCallActive = false;  // Whether a tool call is in progress
    let continuousMode = false;  // Continuous conversation mode
    let autoRestartListening = false;  // Auto-restart after AI finishes speaking

    const player = new window.PCMPlayer({
        sampleRate: 24000,
        onAllEnded: function () {
            // Audio queue drained — if backend already sent tts_end, finalize now
            if (ttsEndReceived) {
                finishSpeaking();
            }
        },
    });

    const vad = new window.EnergyVAD({
        threshold: 0.003,
        smoothingFrames: 1,
        onSpeechStart: () => {
            // User is actually speaking — animate the indicator
            ui.setUserSpeakingVolume(1);  // Full volume on speech detected
            if (isAiSpeaking) {
                player.stop();
                send({ type: 'interrupt' });
            }
            // In continuous mode, auto-start recording if not already recording
            if (continuousMode && !isRecording && !isAiSpeaking) {
                startRecording();
            }
        },
        onSpeechEnd: () => ui.setUserSpeakingVolume(0.3),  // Return to ambient level
    });

    function getApiKey() {
        const params = new URLSearchParams(window.location.search);
        return params.get('api_key') || localStorage.getItem('openclaw_api_key') || '';
    }

    function wsUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const key = getApiKey();
        const path = '/ws';
        if (key) {
            return `${protocol}//${window.location.host}${path}?api_key=${encodeURIComponent(key)}`;
        }
        return `${protocol}//${window.location.host}${path}`;
    }

    function resetState() {
        isRecording = false;
        isAiSpeaking = false;
        ttsEndReceived = false;
        assistantStreamingText = '';
        assistantStreamingMessageEl = null;
        player.stop();
        talkButton.setListening(false);
        talkButton.setSpeaking(false);
        interruptButton && interruptButton.setVisible(false);
        ui.setUserSpeaking(false);
        ui.hideLoadingIndicator();
    }

    function connect() {
        ws = new WebSocket(wsUrl());
        ws.onmessage = (event) => handleMessage(JSON.parse(event.data));
        ws.onclose = (event) => {
            resetState();
            if (event.code === 4001) {
                ui.showStatus('API key required');
            } else if (event.code === 4002) {
                ui.showStatus('Invalid API key');
            } else if (event.code === 4003) {
                ui.showStatus('Rate limited — please wait');
            } else {
                ui.showStatus('Reconnecting...');
                setTimeout(connect, 1500);
            }
        };
        ws.onopen = () => {
            ui.hideStatus();
        };
    }

    function send(payload) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(payload));
        }
    }

    function float32ToBase64(float32Array) {
        const bytes = new Uint8Array(float32Array.buffer);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    function finishSpeaking() {
        ttsEndReceived = false;
        setAiSpeaking(false);
        
        // In continuous mode, auto-restart listening after AI finishes
        if (continuousMode && autoRestartListening) {
            autoRestartListening = false;
            // Small delay to ensure clean state
            setTimeout(() => {
                if (!isRecording && !isAiSpeaking) {
                    startRecording();
                }
            }, 200);
        }
    }

    async function startRecording() {
        if (isRecording) return;

        stream = stream || await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
            },
        });

        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        audioContext = new AudioCtx({ sampleRate: 16000 });
        source = audioContext.createMediaStreamSource(stream);
        // Reduced bufferSize from 4096 to 1024 for smoother animation (64ms = ~16fps)
        processor = audioContext.createScriptProcessor(1024, 1, 1);

        processor.onaudioprocess = (event) => {
            if (!isRecording) return;
            const audioData = event.inputBuffer.getChannelData(0);
            const vadResult = vad.update(audioData);
            // Update volume indicator in real-time (0-1 normalized)
            ui.setUserSpeakingVolume(Math.min(1, vadResult.energy * 50));
            send({ type: 'audio', data: float32ToBase64(audioData) });
        };

        source.connect(processor);
        processor.connect(audioContext.destination);

        isRecording = true;
        talkButton.setListening(true);
        // Show indicator immediately when recording starts
        ui.setUserSpeaking(true);
        send({ type: 'start_listening' });
    }

    function stopRecording() {
        if (!isRecording) return;
        isRecording = false;
        talkButton.setListening(false);

        if (processor) {
            processor.disconnect();
            processor = null;
        }
        if (source) {
            source.disconnect();
            source = null;
        }
        if (audioContext) {
            audioContext.close();
            audioContext = null;
        }

        // Reset VAD state and hide indicator
        vad.reset();
        ui.setUserSpeakingVolume(0);  // Reset bars to minimum
        ui.setUserSpeaking(false);

        send({ type: 'stop_listening' });
        
        // In continuous mode, mark that we should restart after AI finishes
        if (continuousMode) {
            autoRestartListening = true;
        }
    }

    function setAiSpeaking(speaking) {
        isAiSpeaking = speaking;
        talkButton.setSpeaking(speaking);
        interruptButton.setVisible(speaking);
    }

    function handleMessage(msg) {
        switch (msg.type) {
            case 'transcript':
                ui.appendMessage('user', msg.text || '');
                assistantStreamingText = '';
                assistantStreamingMessageEl = null;
                break;
            case 'subtitle_chunk':
                if (!assistantStreamingMessageEl) {
                    assistantStreamingMessageEl = ui.appendMessage('assistant', '');
                }
                if (!ui._loadingEl) {
                    ui.showLoadingIndicator('正在思考...');
                }
                assistantStreamingText += msg.text || '';
                ui.updateStreamingAssistantText(assistantStreamingMessageEl, assistantStreamingText);
                break;
            case 'audio_chunk':
                send({ type: 'client_log', message: 'audio_chunk received: ' + (msg.data ? msg.data.length : 0) + ' bytes' });
                player.enqueue(msg.data, msg.sample_rate);
                break;
            case 'tts_start':
                ttsEndReceived = false;
                setAiSpeaking(true);
                break;
            case 'tts_end':
                ttsEndReceived = true;
                if (!player.isPlaying) {
                    finishSpeaking();
                }
                break;
            case 'tool_call':
                ui.showLoadingIndicator(`正在调用工具: ${msg.tool_name}`);
                break;
            case 'tool_call_end':
                ui.updateLoadingIndicator(`工具执行中...`);
                break;
            case 'response_complete':
                ui.hideLoadingIndicator();
                if (assistantStreamingMessageEl) {
                    ui.updateStreamingAssistantText(assistantStreamingMessageEl, msg.text || assistantStreamingText);
                } else {
                    ui.appendMessage('assistant', msg.text || '');
                }
                break;
            case 'interrupt_complete':
                ttsEndReceived = false;
                ui.hideLoadingIndicator();
                player.stop();
                setAiSpeaking(false);
                break;
            case 'listening_started':
                break;
            case 'listening_stopped':
                if (!isAiSpeaking && !player.isPlaying) {
                    ttsEndReceived = false;
                }
                break;
            case 'pong':
                break;
        }
    }

    interruptButton = new window.InterruptButton(interruptBtnEl, () => {
        player.stop();
        send({ type: 'interrupt' });
        ttsEndReceived = false;
        setAiSpeaking(false);
    });
    interruptButton.setVisible(false);

    // Continuous mode toggle
    if (continuousModeBtnEl) {
        continuousModeBtnEl.addEventListener('click', () => {
            continuousMode = !continuousMode;
            continuousModeBtnEl.classList.toggle('active', continuousMode);
            // Update UI hint
            if (continuousMode) {
                continuousModeBtnEl.title = '连续对话模式：AI 说完后自动开始录音';
            } else {
                continuousModeBtnEl.title = '连续对话模式';
                autoRestartListening = false;
            }
        });
    }

    // Mouse: hold-to-talk (mousedown start, mouseup stop)
    // Skip if touch already handled (prevent duplicate on mobile)
    talkBtnEl.addEventListener('mousedown', () => {
        if (touchHandled) return;
        startRecording();
    });
    talkBtnEl.addEventListener('mouseup', () => {
        if (touchHandled) return;
        stopRecording();
    });
    talkBtnEl.addEventListener('mouseleave', () => {
        if (touchHandled) return;
        stopRecording();
    });

    // Touch: hold-to-talk with preventDefault
    talkBtnEl.addEventListener('touchstart', (event) => {
        touchHandled = true;
        event.preventDefault();
        startRecording();
        // Clear flag after a short delay to allow mouse events on desktop
        setTimeout(() => { touchHandled = false; }, 500);
    }, { passive: false });
    talkBtnEl.addEventListener('touchend', (event) => {
        event.preventDefault();
        stopRecording();
    });

    // Keyboard: Space toggle (press once to start, press again to stop)
    document.addEventListener('keydown', (event) => {
        if (event.code === 'Space' && !event.repeat) {
            event.preventDefault();
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
    });

    connect();

    setInterval(() => {
        send({ type: 'ping' });
    }, 30000);

    // Clear history button
    if (clearHistoryBtnEl) {
        clearHistoryBtnEl.addEventListener('click', () => {
            ui.clearMessages();
        });
    }
})();
