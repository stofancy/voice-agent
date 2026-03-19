(function () {
    function UIController() {
        this.messagesContainer = document.getElementById('messagesContainer');
        this.userSpeakingIndicator = document.getElementById('userSpeakingIndicator');
        this.topBar = document.getElementById('topBar');
        this.historyBtn = document.getElementById('historyBtn');

        this.lastScrollTop = 0;
        this.historyCollapsed = false;
        this._bindScrollBehavior();
        this._bindHistoryToggle();
    }

    UIController.prototype._bindScrollBehavior = function () {
        this.messagesContainer.addEventListener('scroll', () => {
            const top = this.messagesContainer.scrollTop;
            const scrollingDown = top > this.lastScrollTop;
            this.topBar.classList.toggle('hidden', scrollingDown && top > 30);
            this.lastScrollTop = top;
        });
    };

    UIController.prototype._bindHistoryToggle = function () {
        if (!this.historyBtn) return;

        this.historyBtn.addEventListener('click', () => {
            this.historyCollapsed = !this.historyCollapsed;
            this.messagesContainer.classList.toggle('history-collapsed', this.historyCollapsed);
            this.historyBtn.classList.toggle('active', this.historyCollapsed);
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
    };

    UIController.prototype.setUserSpeakingAnimation = function (active) {
        this.userSpeakingIndicator.classList.toggle('active', Boolean(active));
    };

    UIController.prototype.showStatus = function (text) {
        if (!this._statusEl) {
            this._statusEl = document.createElement('div');
            this._statusEl.className = 'connection-status';
            document.body.appendChild(this._statusEl);
        }
        this._statusEl.textContent = text;
        this._statusEl.style.display = 'block';
    };

    UIController.prototype.hideStatus = function () {
        if (this._statusEl) {
            this._statusEl.style.display = 'none';
        }
    };

    UIController.prototype.clearMessages = function () {
        this.messagesContainer.innerHTML = '';
    };

    window.UIController = UIController;
})();
