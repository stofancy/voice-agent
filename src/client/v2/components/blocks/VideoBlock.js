(function () {
    window.VideoBlock = function VideoBlock(url, title) {
        if (!url) return '';
        const safeUrl = window.SanitizeUtils.escapeHtml(url);
        const label = window.SanitizeUtils.escapeHtml(title || 'Video');
        return `<p class="message-text"><a href="${safeUrl}" target="_blank" rel="noopener noreferrer">🎬 ${label}</a></p>`;
    };
})();
