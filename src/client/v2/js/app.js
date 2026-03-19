(function () {
    const talkBtnEl = document.getElementById('talkBtn');
    const interruptBtnEl = document.getElementById('interruptBtn');
    const clearHistoryBtnEl = document.getElementById('clearHistoryBtn');

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
        threshold: 0.012,
        smoothingFrames: 3,
        onSpeechStart: () => {
            ui.setUserSpeaking(true);
            if (isAiSpeaking) {
                player.stop();
                send({ type: 'interrupt' });
            }
        },
        onSpeechEnd: () => ui.setUserSpeaking(false),
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
        processor = audioContext.createScriptProcessor(4096, 1, 1);

        processor.onaudioprocess = (event) => {
            if (!isRecording) return;
            const audioData = event.inputBuffer.getChannelData(0);
            vad.update(audioData);
            send({ type: 'audio', data: float32ToBase64(audioData) });
        };

        source.connect(processor);
        processor.connect(audioContext.destination);

        isRecording = true;
        talkButton.setListening(true);
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

        // Reset VAD state to clear "user speaking" indicator
        vad.reset();
        ui.setUserSpeaking(false);

        send({ type: 'stop_listening' });
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
                assistantStreamingText += msg.text || '';
                if (!assistantStreamingMessageEl) {
                    assistantStreamingMessageEl = ui.appendMessage('assistant', '');
                }
                ui.updateStreamingAssistantText(assistantStreamingMessageEl, assistantStreamingText);
                break;
            case 'audio_chunk':
                player.enqueue(msg.data, msg.sample_rate);
                break;
            case 'tts_start':
                ttsEndReceived = false;
                setAiSpeaking(true);
                break;
            case 'tts_end':
                // Don't immediately stop speaking — wait for audio queue to drain
                ttsEndReceived = true;
                if (!player.isPlaying) {
                    finishSpeaking();
                }
                break;
            case 'response_complete':
                if (assistantStreamingMessageEl) {
                    ui.updateStreamingAssistantText(assistantStreamingMessageEl, msg.text || assistantStreamingText);
                } else {
                    ui.appendMessage('assistant', msg.text || '');
                }
                break;
            case 'interrupt_complete':
                ttsEndReceived = false;
                player.stop();
                setAiSpeaking(false);
                break;
            case 'listening_started':
                break;
            case 'listening_stopped':
                // Turn is fully done — ensure clean state
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
