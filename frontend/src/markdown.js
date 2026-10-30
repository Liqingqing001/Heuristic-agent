// Markdown 渲染统一入口：先解析，再用 DOMPurify 消毒，避免 AI 输出里的
// <script> / onerror 之类的脚本注入（marked 默认不做 XSS 过滤）。
import { marked } from 'marked'
import DOMPurify from 'dompurify'

export function renderMarkdown(text) {
  const html = marked.parse(text || '')
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
}
