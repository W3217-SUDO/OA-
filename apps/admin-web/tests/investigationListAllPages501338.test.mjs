// 501338（fwl 11-04）：调查大厅线索列表要把 100 条以后的也取出来，总条数和老系统一致。
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import ts from "typescript";

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const code = ts.transpileModule(read("investigation/loadRemainingPages.ts"), { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const { loadRemainingPages } = await import(`data:text/javascript,${encodeURIComponent(code)}`);

test("554 条取齐第 2 到第 6 页，按页码顺序，最多 4 个并发", async () => {
  let running = 0, peak = 0;
  const pages = [];
  const rows = await loadRemainingPages(554, async (page) => {
    running += 1; peak = Math.max(peak, running); pages.push(page);
    await new Promise((resolve) => setTimeout(resolve, 5));
    running -= 1;
    return Array.from({ length: page === 6 ? 54 : 100 }, (_, index) => `${page}-${index}`);
  });
  assert.equal(rows.length, 454);
  assert.equal(rows[0], "2-0");
  assert.equal(rows.at(-1), "6-53");
  assert.deepEqual([...pages].sort((a, b) => a - b), [2, 3, 4, 5, 6]);
  assert.ok(peak <= 4);
  assert.deepEqual(await loadRemainingPages(100, async () => ["x"]), []);
});

test("所有调查大厅列表都在总数超过 100 时取后面几页", () => {
  const page = read("investigation/InvestigationCenterPage.tsx");
  assert.match(page, /if \(initialTab !== "notary-query-files" && data\.total > loadedRows\.length\)/);
  assert.match(page, /api\.get\("\/records", \{ params: \{ \.\.\.listParams, page \} \}\)/);
});
