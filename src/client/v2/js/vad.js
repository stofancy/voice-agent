(function () {
    function EnergyVAD(options) {
        this.threshold = options && options.threshold ? options.threshold : 0.012;
        this.smoothingFrames = options && options.smoothingFrames ? options.smoothingFrames : 3;
        this.onSpeechStart = options && options.onSpeechStart ? options.onSpeechStart : function () {};
        this.onSpeechEnd = options && options.onSpeechEnd ? options.onSpeechEnd : function () {};

        this.speaking = false;
        this.speechFrames = 0;
        this.silenceFrames = 0;
    }

    EnergyVAD.prototype.update = function (float32Array) {
        if (!float32Array || !float32Array.length) {
            return this.speaking;
        }

        let total = 0;
        for (let i = 0; i < float32Array.length; i++) {
            total += Math.abs(float32Array[i]);
        }

        const energy = total / float32Array.length;
        const hasSpeech = energy > this.threshold;

        if (hasSpeech) {
            this.speechFrames += 1;
            this.silenceFrames = 0;
            if (!this.speaking && this.speechFrames >= this.smoothingFrames) {
                this.speaking = true;
                this.onSpeechStart();
            }
        } else {
            this.silenceFrames += 1;
            this.speechFrames = 0;
            if (this.speaking && this.silenceFrames >= this.smoothingFrames) {
                this.speaking = false;
                this.onSpeechEnd();
            }
        }

        return this.speaking;
    };

    EnergyVAD.prototype.reset = function () {
        this.speaking = false;
        this.speechFrames = 0;
        this.silenceFrames = 0;
    };

    window.EnergyVAD = EnergyVAD;
})();
