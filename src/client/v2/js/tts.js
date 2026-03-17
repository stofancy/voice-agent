(function () {
    function PCMPlayer() {
        this.queue = [];
        this.isPlaying = false;
        this.currentSource = null;
        this.currentContext = null;
    }

    PCMPlayer.prototype.enqueue = function (base64Data, sampleRate) {
        this.queue.push({ data: base64Data, sampleRate: sampleRate || 24000 });
        if (!this.isPlaying) {
            this.playNext();
        }
    };

    PCMPlayer.prototype.playNext = function () {
        if (this.queue.length === 0) {
            this.isPlaying = false;
            return;
        }

        this.isPlaying = true;
        const item = this.queue.shift();

        try {
            const binary = atob(item.data);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                bytes[i] = binary.charCodeAt(i);
            }

            const int16 = new Int16Array(bytes.buffer);
            const float32 = new Float32Array(int16.length);
            for (let i = 0; i < int16.length; i++) {
                float32[i] = int16[i] / 32768;
            }

            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            const ctx = new AudioCtx({ sampleRate: item.sampleRate });
            this.currentContext = ctx;

            const buffer = ctx.createBuffer(1, float32.length, item.sampleRate);
            buffer.copyToChannel(float32, 0);

            const source = ctx.createBufferSource();
            source.buffer = buffer;
            source.connect(ctx.destination);
            this.currentSource = source;

            source.onended = () => {
                this.currentSource = null;
                if (this.currentContext) {
                    this.currentContext.close();
                    this.currentContext = null;
                }
                this.playNext();
            };

            source.start(0);
        } catch (_err) {
            this.playNext();
        }
    };

    PCMPlayer.prototype.stop = function () {
        this.queue = [];
        this.isPlaying = false;

        if (this.currentSource) {
            try {
                this.currentSource.stop(0);
            } catch (_err) {
            }
            this.currentSource = null;
        }

        if (this.currentContext) {
            this.currentContext.close();
            this.currentContext = null;
        }
    };

    window.PCMPlayer = PCMPlayer;
})();
