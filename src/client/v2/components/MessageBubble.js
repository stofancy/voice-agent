(function () {
    const renderers = {
        text: (block) =>
            window.TextBlock ? window.TextBlock(block.text || '') : `<p class="message-text">${window.SanitizeUtils.renderMarkdownLite(block.text || '')}</p>`,
        image: (block) =>
            window.ImageBlock ? window.ImageBlock(block.url, block.alt) : '',
        link: (block) =>
            window.LinkBlock ? window.LinkBlock(block.url, block.text) : '',
        video: (block) =>
            window.VideoBlock ? window.VideoBlock(block.url, block.title) : '',
        html: (block) =>
            window.HtmlBlock ? window.HtmlBlock(block.html) : `<div class="message-text">${window.SanitizeUtils.renderMarkdownLite(block.html || '')}</div>`,
    };

    function renderBlock(block) {
        if (!block || typeof block !== 'object') {
            return '';
        }

        const renderer = renderers[block.type];
        return renderer ? renderer(block) : '';
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
            const blocks = window.SanitizeUtils.parseTextToBlocks(String(payload || ''));
            const html = blocks.map(renderBlock).join('');
            content.insertAdjacentHTML('beforeend', html || '<p class="message-text"></p>');
        }

        message.appendChild(content);
        return message;
    }

    window.MessageBubble = {
        createMessageElement,
    };
})();
