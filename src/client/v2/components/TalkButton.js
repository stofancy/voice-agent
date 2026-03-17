(function () {
    function TalkButton(element) {
        this.element = element;
    }

    TalkButton.prototype.setListening = function (listening) {
        this.element.classList.toggle('listening', Boolean(listening));
    };

    TalkButton.prototype.setSpeaking = function (speaking) {
        this.element.classList.toggle('speaking', Boolean(speaking));
    };

    window.TalkButton = TalkButton;
})();
