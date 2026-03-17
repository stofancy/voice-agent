(function () {
    window.TextBlock = function TextBlock(text) {
        return `<p class=\"message-text\">${window.SanitizeUtils.renderMarkdownLite(text || '')}</p>`;
    };
})();
