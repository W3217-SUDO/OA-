import DOMPurify from "dompurify";
import { Marked } from "marked";
import TurndownService from "turndown";

const allowedTags = ["p", "div", "br", "h1", "h2", "h3", "strong", "b", "em", "i", "ul", "ol", "li"];
const supportedTokens = new Set(["space", "paragraph", "heading", "text", "strong", "em", "list", "list_item", "br", "escape", "html"]);
const parser = new Marked({
  gfm: false,
  async: false,
  walkTokens(token) {
    if (!supportedTokens.has(token.type) || (token.type === "heading" && token.depth > 3)) {
      throw new Error("当前在线编辑仅支持一级至三级标题、粗体、斜体及普通列表；原文件未修改");
    }
  },
  renderer: {
    html({ text }) {
      return text.replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);
    },
  },
});
const serializer = new TurndownService({ headingStyle: "atx", bulletListMarker: "-", emDelimiter: "*", strongDelimiter: "**" });

export function sanitizePersonalEditorHtml(html: string): string {
  return DOMPurify.sanitize(html, { ALLOWED_TAGS: allowedTags, ALLOWED_ATTR: ["start"], ALLOW_DATA_ATTR: false, ALLOW_ARIA_ATTR: false });
}

export function personalMarkdownToHtml(value: string): string {
  return sanitizePersonalEditorHtml(parser.parse(value, { async: false }));
}

export function personalHtmlToMarkdown(html: string): string {
  return serializer.turndown(sanitizePersonalEditorHtml(html));
}
