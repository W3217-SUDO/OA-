import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const globalSearchSource = fs.readFileSync(new URL("./src/GlobalSearch.tsx", import.meta.url), "utf8");

test("topbar uses one unified search for menus and case keywords", () => {
  assert.match(source, /<GlobalSearch/);
  assert.match(globalSearchSource, /placeholder="搜索菜单、案号、法院号、案件名、客户名"/);
  assert.match(globalSearchSource, /api\.get\("\/search", \{ params: \{ q \} \}\)/);
  assert.doesNotMatch(source, /quick-case-search|案件快捷搜索/);
});
