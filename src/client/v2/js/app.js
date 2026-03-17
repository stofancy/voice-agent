(function () {
    const talkBtnEl = document.getElementById('talkBtn');
    const interruptBtnEl = document.getElementById('interruptBtn');

    const talkButton = new window.TalkButton(talkBtnEl);
    const ui = new window.UIController();
    const player = new window.PCMPlayer();

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
        const path = '/v2/ws';
        if (key) {
            return `${protocol}//${window.location.host}${path}?api_key=${encodeURIComponent(key)}`;
        }
        return `${protocol}//${window.location.host}${path}`;
    }

    function connect() {
        ws = new WebSocket(wsUrl());
        ws.onmessage = (event) => handleMessage(JSON.parse(event.data));
        ws.onclose = () => setTimeout(connect, 1500);
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
                setAiSpeaking(true);
                break;
            case 'tts_end':
                setAiSpeaking(false);
                break;
            case 'response_complete':
                if (assistantStreamingMessageEl) {
                    ui.updateStreamingAssistantText(assistantStreamingMessageEl, msg.text || assistantStreamingText);
                } else {
                    ui.appendMessage('assistant', msg.text || '');
                }
                break;
            case 'interrupt_complete':
                setAiSpeaking(false);
                break;
            default:
                break;
        }
    }

    interruptButton = new window.InterruptButton(interruptBtnEl, () => {
        player.stop();
        send({ type: 'interrupt' });
        setAiSpeaking(false);
    });
    interruptButton.setVisible(false);

    talkBtnEl.addEventListener('mousedown', () => startRecording());
    talkBtnEl.addEventListener('mouseup', () => stopRecording());
    talkBtnEl.addEventListener('mouseleave', () => stopRecording());
    talkBtnEl.addEventListener('touchstart', (event) => {
        event.preventDefault();
        startRecording();
    }, { passive: false });
    talkBtnEl.addEventListener('touchend', () => stopRecording());

    document.addEventListener('keydown', (event) => {
        if (event.code === 'Space' && !event.repeat) {
            event.preventDefault();
            if (!isRecording) startRecording();
        }
    });
    document.addEventListener('keyup', (event) => {
        if (event.code === 'Space') {
            event.preventDefault();
            stopRecording();
        }
    });

    connect();

    setInterval(() => {
        send({ type: 'ping' });
    }, 30000);
})();
