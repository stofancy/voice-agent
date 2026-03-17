(function () {
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    function renderMarkdownLite(text) {
        const safe = escapeHtml(text || '');
        return safe
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
            .replace(/\n/g, '<br>');
    }

    function parseTextToBlocks(text) {
        const input = String(text || '');
        const lines = input.split(/\r?\n/);
        const blocks = [];

        const imagePattern = /^!\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)$/;
        const linkPattern = /^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/;
        const videoPattern = /^(https?:\/\/[^\s]+\/(watch\?v=|video\/|shorts\/)[^\s]+)$/i;

        for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line) {
                continue;
            }

            const imageMatch = line.match(imagePattern);
            if (imageMatch) {
                blocks.push({ type: 'image', alt: imageMatch[1], url: imageMatch[2] });
                continue;
            }

            const linkMatch = line.match(linkPattern);
            if (linkMatch) {
                blocks.push({ type: 'link', text: linkMatch[1], url: linkMatch[2] });
                continue;
            }

            if (line.startsWith('<') && line.endsWith('>')) {
                blocks.push({ type: 'html', html: line });
                continue;
            }

            if (line.match(videoPattern)) {
                blocks.push({ type: 'video', url: line, title: 'Video' });
                continue;
            }

            blocks.push({ type: 'text', text: rawLine });
        }

        return blocks;
    }

    window.SanitizeUtils = {
        escapeHtml,
        renderMarkdownLite,
        parseTextToBlocks,
    };
})();
