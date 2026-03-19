(function () {
    function PCMPlayer(options) {
        this.queue = [];
        this.isPlaying = false;
        this.currentSource = null;
        this.ctx = null;
        this.defaultSampleRate = (options && options.sampleRate) || 24000;
        this.onAllEnded = (options && options.onAllEnded) || null;
    }

    PCMPlayer.prototype._ensureContext = function (sampleRate) {
        if (this.ctx && this.ctx.state !== 'closed') {
            return this.ctx;
        }
        var AudioCtx = window.AudioContext || window.webkitAudioContext;
        this.ctx = new AudioCtx({ sampleRate: sampleRate });
        return this.ctx;
    };

    PCMPlayer.prototype._decodeChunk = function (base64Data, sampleRate) {
        var binary = atob(base64Data);
        var bytes = new Uint8Array(binary.length);
        for (var i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }

        var audioData = bytes;
        var actualSampleRate = sampleRate;

        // WAV header detection (RIFF....WAVE)
        if (bytes.length > 44 &&
            bytes[0] === 0x52 && bytes[1] === 0x49 &&
            bytes[2] === 0x46 && bytes[3] === 0x46 &&
            bytes[8] === 0x57 && bytes[9] === 0x41 &&
            bytes[10] === 0x56 && bytes[11] === 0x45) {
            actualSampleRate = bytes[24] | (bytes[25] << 8) | (bytes[26] << 16) | (bytes[27] << 24);
            audioData = bytes.slice(44);
        }

        var int16 = new Int16Array(audioData.buffer, audioData.byteOffset, audioData.byteLength / 2);
        var float32 = new Float32Array(int16.length);
        for (var j = 0; j < int16.length; j++) {
            float32[j] = int16[j] / 32768;
        }

        return { samples: float32, sampleRate: actualSampleRate };
    };

    PCMPlayer.prototype.enqueue = function (base64Data, sampleRate) {
        this.queue.push({ data: base64Data, sampleRate: sampleRate || this.defaultSampleRate });
        if (!this.isPlaying) {
            this.playNext();
        }
    };

    PCMPlayer.prototype.playNext = function () {
        if (this.queue.length === 0) {
            this.isPlaying = false;
            if (typeof this.onAllEnded === 'function') {
                this.onAllEnded();
            }
            return;
        }

        this.isPlaying = true;
        var item = this.queue.shift();
        var self = this;

        try {
            var decoded = this._decodeChunk(item.data, item.sampleRate);
            var ctx = this._ensureContext(decoded.sampleRate);

            // Resume context if suspended (browser autoplay policy)
            if (ctx.state === 'suspended') {
                ctx.resume();
            }

            var buffer = ctx.createBuffer(1, decoded.samples.length, decoded.sampleRate);
            buffer.copyToChannel(decoded.samples, 0);

            var source = ctx.createBufferSource();
            source.buffer = buffer;
            source.connect(ctx.destination);
            self.currentSource = source;

            source.onended = function () {
                self.currentSource = null;
                self.playNext();
            };

            source.start(0);
        } catch (_err) {
            self.playNext();
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
    };

    PCMPlayer.prototype.destroy = function () {
        this.stop();
        if (this.ctx && this.ctx.state !== 'closed') {
            this.ctx.close();
            this.ctx = null;
        }
    };

    window.PCMPlayer = PCMPlayer;
})();
