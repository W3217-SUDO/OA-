import type { ReactNode } from "react";

// 分享文案里的网址：只认 http/https，遇到空白、中文或中文标点就结束（如淘宝“…https://m.tb.cn/h.xxx CZ225 我分享给你…”）
const URL_PATTERN = /https?:\/\/[^\s　-〿一-鿿＀-￯<>"'“”‘’]+/gi;
const TRAILING_PUNCTUATION = /[.,;:!?)\]}]+$/;

export type TextPart = { text: string; href?: string };

/** 把一段文字拆成普通文字和网址；只接受 http/https，javascript: 等一律当普通文字。 */
export function splitLinkText(value: unknown): TextPart[] {
  const text = String(value ?? "");
  const parts: TextPart[] = [];
  let last = 0;
  for (const match of text.matchAll(URL_PATTERN)) {
    let url = match[0];
    const trailing = url.match(TRAILING_PUNCTUATION)?.[0] || "";
    if (trailing) url = url.slice(0, -trailing.length);
    const start = match.index ?? 0;
    let href = "";
    try {
      const parsed = new URL(url);
      if (parsed.protocol === "http:" || parsed.protocol === "https:") href = parsed.href;
    } catch {
      href = "";
    }
    if (!href) continue;
    if (start > last) parts.push({ text: text.slice(last, start) });
    parts.push({ text: url, href });
    last = start + url.length;
  }
  if (last < text.length) parts.push({ text: text.slice(last) });
  return parts;
}

/** 显示店铺链接、产品链接等：文字里的网址可点击、新窗口打开，其余文字照常显示（钉钉手机内核兼容，只用普通样式）。 */
export function LinkifiedText({ value, empty = "—" }: { value: unknown; empty?: ReactNode }) {
  const parts = splitLinkText(value);
  if (!parts.length || !String(value ?? "").trim()) return <>{empty}</>;
  return <span className="linkified-text" style={{ wordBreak: "break-all" }}>
    {parts.map((part, index) => part.href
      ? <a key={index} href={part.href} target="_blank" rel="noopener noreferrer">{part.text}</a>
      : <span key={index}>{part.text}</span>)}
  </span>;
}
