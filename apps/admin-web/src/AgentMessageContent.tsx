import type { ReactNode } from "react";

type Block =
  | { type: "heading"; text: string; tone: "default" | "summary" | "risk" }
  | { type: "paragraph"; text: string }
  | { type: "list"; ordered: boolean; items: string[] };

const HEADING_PATTERN = /^(重点结论|结论|事实|关键信息|材料现状|期限风险|主要风险|风险提示|建议|建议工作清单|下一步|待办事项|行动清单)[：:]?$/;

function stripMarkdown(value: string) {
  return value.replace(/^#{1,6}\s*/, "").replace(/\*\*([^*]+)\*\*/g, "$1").replace(/__([^_]+)__/g, "$1").trim();
}

function headingTone(text: string): "default" | "summary" | "risk" {
  if (/结论|关键信息/.test(text)) return "summary";
  if (/风险/.test(text)) return "risk";
  return "default";
}

function parseBlocks(content: string): Block[] {
  const blocks: Block[] = [];
  const lines = content.replace(/\r\n?/g, "\n").split("\n");
  let paragraph: string[] = [];
  let list: Extract<Block, { type: "list" }> | null = null;
  const flushParagraph = () => { if (paragraph.length) blocks.push({ type: "paragraph", text: paragraph.join(" ").trim() }); paragraph = []; };
  const flushList = () => { if (list?.items.length) blocks.push(list); list = null; };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) { flushParagraph(); flushList(); continue; }
    const heading = stripMarkdown(line);
    if (/^#{1,6}\s+/.test(line) || /^\*\*[^*]+\*\*$/.test(line) || HEADING_PATTERN.test(heading)) {
      flushParagraph(); flushList();
      blocks.push({ type: "heading", text: heading.replace(/[：:]$/, ""), tone: headingTone(heading) });
      continue;
    }
    const itemMatch = line.match(/^(?:(\d+)[.、]|[-*•])\s*(.+)$/);
    if (itemMatch) {
      flushParagraph();
      const ordered = Boolean(itemMatch[1]);
      if (!list || list.ordered !== ordered) flushList();
      list ||= { type: "list", ordered, items: [] };
      list.items.push(itemMatch[2].trim());
      continue;
    }
    flushList(); paragraph.push(line);
  }
  flushParagraph(); flushList();
  return blocks;
}

function renderInline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|__[^_]+__)/g).filter(Boolean).map((part, index) => {
    const emphasized = part.match(/^(?:\*\*|__)(.+)(?:\*\*|__)$/);
    return emphasized ? <strong key={index}>{emphasized[1]}</strong> : part.replace(/\*\*|__/g, "");
  });
}

export function AgentMessageContent({ content }: { content: string }) {
  return <div className="agent-message-content">{parseBlocks(content).map((block, index) => {
    if (block.type === "heading") return <h3 key={index} className={`agent-message-heading agent-message-heading-${block.tone}`}>{block.text}</h3>;
    if (block.type === "paragraph") return <p key={index}>{renderInline(block.text)}</p>;
    const ListTag = block.ordered ? "ol" : "ul";
    return <ListTag key={index}>{block.items.map((item, itemIndex) => <li key={itemIndex}>{renderInline(item)}</li>)}</ListTag>;
  })}</div>;
}
