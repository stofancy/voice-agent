(function () {
    window.HtmlBlock = function HtmlBlock(html) {
        const safe = window.SanitizeUtils.renderMarkdownLite(String(html || ''));
        return `<div class="message-text">${safe}</div>`;
    };
})();
