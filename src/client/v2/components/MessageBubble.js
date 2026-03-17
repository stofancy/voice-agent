(function () {
    function renderBlock(block) {
        if (!block || typeof block !== 'object') {
            return '';
        }

        switch (block.type) {
            case 'text':
                return `<p class="message-text">${window.SanitizeUtils.renderMarkdownLite(block.text || '')}</p>`;
            case 'image':
                if (!block.url) return '';
                return `<img src="${window.SanitizeUtils.escapeHtml(block.url)}" alt="${window.SanitizeUtils.escapeHtml(block.alt || 'image')}" style="max-width:100%;border-radius:10px;" />`;
            case 'link':
                if (!block.url) return '';
                return `<p class="message-text"><a href="${window.SanitizeUtils.escapeHtml(block.url)}" target="_blank" rel="noopener noreferrer">${window.SanitizeUtils.escapeHtml(block.text || block.url)}</a></p>`;
            case 'video':
                if (!block.url) return '';
                return `<p class="message-text"><a href="${window.SanitizeUtils.escapeHtml(block.url)}" target="_blank" rel="noopener noreferrer">🎬 ${window.SanitizeUtils.escapeHtml(block.title || 'Video')}</a></p>`;
            case 'html':
                return `<div class="message-text">${window.SanitizeUtils.renderMarkdownLite(block.html || '')}</div>`;
            default:
                return '';
        }
    }

    function createMessageElement(role, payload) {
        const message = document.createElement('div');
        message.className = `message ${role === 'user' ? 'user' : 'assistant'}`;

        const content = document.createElement('div');
        content.className = 'message-content';

        const sender = document.createElement('span');
        sender.className = 'message-sender';
        sender.textContent = role === 'user' ? '👤 用户' : '🤖 AI';

        content.appendChild(sender);

        if (Array.isArray(payload)) {
            const html = payload.map(renderBlock).join('');
            content.insertAdjacentHTML('beforeend', html || '<p class="message-text"></p>');
        } else {
            const textNode = document.createElement('p');
            textNode.className = 'message-text';
            textNode.innerHTML = window.SanitizeUtils.renderMarkdownLite(String(payload || ''));
            content.appendChild(textNode);
        }

        message.appendChild(content);
        return message;
    }

    window.MessageBubble = {
        createMessageElement,
    };
})();
