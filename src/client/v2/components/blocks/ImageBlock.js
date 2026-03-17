(function () {
    window.ImageBlock = function ImageBlock(url, alt) {
        if (!url) return '';
        return `<img src=\"${window.SanitizeUtils.escapeHtml(url)}\" alt=\"${window.SanitizeUtils.escapeHtml(alt || 'image')}\" style=\"max-width:100%;border-radius:10px;\" />`;
    };
})();
