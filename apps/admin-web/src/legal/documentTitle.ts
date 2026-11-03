// 陶威 11-03：保存 AI 回答为 Word 时，文件名要用文书标题，不能拿回答开头的说明句当文件名。
// 依次取：Markdown 标题行（# 标题）→ 单独一行的加粗标题（**标题**）→ 第一行像标题的短句 → 第一行文字。

const strip = (line: string) => line.replace(/^[#>*\-\s]+/, "").replace(/[*_`]+/g, "").trim();
const looksLikeSentence = (text: string) => text.length > 30 || /[：:]$/.test(text) || /[，。；！？,;!?]/.test(text);

export function documentTitleFromContent(content: string): string {
  const lines = String(content || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const heading = lines.find((line) => /^#{1,3}\s+\S/.test(line));
  const boldLine = lines.find((line) => /^\*\*[^*]{2,40}\*\*$/.test(line));
  const shortLine = lines.map(strip).find((text) => text && !looksLikeSentence(text));
  const title = (heading && strip(heading)) || (boldLine && strip(boldLine)) || shortLine || strip(lines[0] || "");
  return title.replace(/[\\/:*?"<>|]+/g, " ").trim().slice(0, 60);
}
