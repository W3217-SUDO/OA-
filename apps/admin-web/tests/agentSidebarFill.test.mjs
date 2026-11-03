// 陶威 11-03：智能体中心左侧栏撑满高度，个人空间最近会话可以多展开。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");

test("智能体中心左侧栏撑满高度：最近会话往下撑满、案件空间按比例分、底部按钮固定（陶威 11-03）", () => {
  const css = read("../src/personal-agent/ai-chat-page.css");
  const block = css.split("陶威 11-03：左侧栏撑满高度")[1].split("\n}\n")[0];
  assert.match(block, /\.assistant-workspace-navigation \{\n    flex: 1 1 0;\n    min-height: 0;/);
  assert.match(block, /\.assistant-workspace-history\.is-in-space \{\n    flex: 3 1 0;/);
  assert.match(block, /\.assistant-workspace-projects\.is-expanded \{\n    flex: 1 1 0;/);
  assert.match(block, /\.assistant-workspace-footer \{\n    margin-top: auto;/);
  assert.doesNotMatch(block.replace(/\/\*[\s\S]*?\*\//g, ""), /color-mix\(|:has\(|@container|dvh/, "兼容钉钉 Chrome 100");
  assert.match(read("../src/personal-agent/ConversationWorkspaceNavigation.tsx"), /assistant-workspace-projects\$\{expanded \? " is-expanded" : ""\}/);
});
