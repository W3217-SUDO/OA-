import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(new URL(`../src/personal-agent/${path}`, import.meta.url), "utf8");

test("当前会话整行高亮，并在不在前 50 条时放到最上面", () => {
  const manager = read("ConversationManager.tsx");
  assert.match(manager, /item\.id === activeId \? " active is-current-conversation" : ""/);
  assert.match(manager, /scrollIntoView\(\{ block: "nearest" \}\)/);
  assert.match(manager, /当前会话（较早）/);
  assert.match(manager, /import "\.\/activeConversation\.css"/);
});

test("任务入口在进入其会话时高亮并展开", () => {
  const sidebar = read("AssistantWorkspaceSidebar.tsx");
  assert.match(sidebar, /activeEntry === entry\.key \? "is-current-entry"/);
  assert.match(sidebar, /setExpanded\(\(keys\) => keys\.includes\(activeEntry\)/);
});

test("高亮样式兼容钉钉 Chrome 100", () => {
  const css = read("activeConversation.css").replace(/\/\*[\s\S]*?\*\//g, "");
  assert.doesNotMatch(css, /:has\(|color-mix|@container|dvh/);
  assert.match(css, /\.is-current-conversation[^{]*\{[^}]*inset 3px 0 0/);
  assert.match(css, /font-weight: 600/);
});
