/**
 * Markdown 渲染工具
 * 支持代码块、粗体、斜体、链接渲染
 */

export function renderMarkdown(text: string): string {
  if (!text) return '';
  
  return text
    // 代码块 (```code```)
    .replace(/```([\s\S]*?)```/g, '<code class="block">$1</code>')
    // 行内代码 (`code`)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // 粗体 (**text**)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // 斜体 (*text*)
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    // 链接 ([text](url))
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    // 换行
    .replace(/\n/g, '<br>');
}

/**
 * 安全的 HTML 渲染（防止 XSS）
 * 在实际使用中，应该使用 DOMPurify 等库进行清理
 * 这里简化处理，仅用于内部可信内容
 */
export function renderMarkdownSafe(text: string): string {
  // 首先渲染 Markdown
  const html = renderMarkdown(text);
  
  // 简单的 XSS 防护（生产环境应该使用 DOMPurify）
  return html
    .replace(/javascript:/gi, '')
    .replace(/on\w+=/gi, '');
}
