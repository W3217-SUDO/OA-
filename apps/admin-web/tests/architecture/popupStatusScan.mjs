import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const srcRoot = fileURLToPath(new URL("../../src/", import.meta.url));

function sourceFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) return sourceFiles(target);
    return /\.(?:tsx?|mjs)$/.test(entry.name) && !entry.name.endsWith(".d.ts") ? [target] : [];
  });
}

/** 取出 <Modal ...> / <Drawer ...> 的开始标签，按花括号配对跳过属性里的表达式。 */
function openingTags(source) {
  const tags = [];
  for (const match of source.matchAll(/<(Modal|Drawer)\b/g)) {
    let depth = 0;
    let index = match.index + match[0].length;
    for (; index < source.length; index += 1) {
      const char = source[index];
      if (char === "{") depth += 1;
      else if (char === "}") depth -= 1;
      else if (char === ">" && depth === 0) break;
    }
    tags.push({ kind: match[1], text: source.slice(match.index, index) });
  }
  return tags;
}

function attribute(tag, name) {
  const match = tag.match(new RegExp(`\\s${name}=(\\{(?:[^{}]|\\{[^{}]*\\})*\\}|"[^"]*"|'[^']*')`));
  return match?.[1];
}

/** 写死的宽度：属性值里出现三位以上数字或 px/vw/% 字面量；侧滑仍用已不推荐的 width 也算。 */
export function hardcodedPopupWidths(source) {
  return openingTags(source).filter(({ kind, text }) => {
    const width = attribute(text, "width");
    const size = kind === "Drawer" ? attribute(text, "size") : undefined;
    if (kind === "Drawer" && width) return true;
    return [width, size].some((value) => value && /\d{3,}|\d+\s*(?:px|vw|%)|"\d+%"/.test(value));
  }).length;
}

/** 模块里自建的“状态→颜色”表，应改用 components/common/statusTone.ts。 */
export function localStatusColorMaps(source) {
  return [...source.matchAll(/\b(?:const|let)\s+\w*(?:status|asset)\w*colou?rs?\s*(?::[^=\n]+)?=\s*\{/gi)].length;
}

export function scanSources() {
  const popupWidths = {};
  const statusMaps = {};
  for (const file of sourceFiles(srcRoot)) {
    const relative = path.relative(srcRoot, file).split(path.sep).join("/");
    if (relative.startsWith("components/common/")) continue;
    const source = readFileSync(file, "utf8");
    const widths = hardcodedPopupWidths(source);
    const maps = localStatusColorMaps(source);
    if (widths) popupWidths[relative] = widths;
    if (maps) statusMaps[relative] = maps;
  }
  return { popupWidths, statusMaps };
}
