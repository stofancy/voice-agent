(function () {
    function UIController() {
        this.messagesContainer = document.getElementById('messagesContainer');
        this.userSpeakingIndicator = document.getElementById('userSpeakingIndicator');
        this.topBar = document.getElementById('topBar');

        this.lastScrollTop = 0;
        this._bindScrollBehavior();
    }

    UIController.prototype._bindScrollBehavior = function () {
        this.messagesContainer.addEventListener('scroll', () => {
            const top = this.messagesContainer.scrollTop;
            const scrollingDown = top > this.lastScrollTop;
            this.topBar.classList.toggle('hidden', scrollingDown && top > 30);
            this.lastScrollTop = top;
        });
    };

    UIController.prototype.appendMessage = function (role, payload) {
        const element = window.MessageBubble.createMessageElement(role, payload);
        this.messagesContainer.appendChild(element);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        return element;
    };

    UIController.prototype.updateStreamingAssistantText = function (targetElement, text) {
        if (!targetElement) return;
        const textNode = targetElement.querySelector('.message-text');
        if (textNode) {
            textNode.innerHTML = window.SanitizeUtils.renderMarkdownLite(text);
        }
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    };

    UIController.prototype.setUserSpeaking = function (active) {
        this.userSpeakingIndicator.style.display = active ? 'block' : 'none';
        this.userSpeakingIndicator.classList.toggle('active', Boolean(active));
    };

    window.UIController = UIController;
})();
