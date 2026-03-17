(function () {
    window.LinkBlock = function LinkBlock(url, text) {
        if (!url) return '';
        const safeUrl = window.SanitizeUtils.escapeHtml(url);
        const label = window.SanitizeUtils.escapeHtml(text || url);
        return `<p class="message-text"><a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${label}</a></p>`;
    };
})();
