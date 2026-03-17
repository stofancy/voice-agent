(function () {
    function InterruptButton(element, onInterrupt) {
        this.element = element;
        this.onInterrupt = onInterrupt;

        this.element.addEventListener('click', () => {
            this.flash();
            if (typeof this.onInterrupt === 'function') {
                this.onInterrupt();
            }
        });
    }

    InterruptButton.prototype.setVisible = function (visible) {
        this.element.style.display = visible ? 'inline-flex' : 'none';
    };

    InterruptButton.prototype.flash = function () {
        this.element.classList.add('flash');
        setTimeout(() => this.element.classList.remove('flash'), 220);
    };

    window.InterruptButton = InterruptButton;
})();
