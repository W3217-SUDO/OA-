// 陶威 11-03：打开案件详情时线索分页另起请求序号，不能把文档、费用的返回当成过期丢掉（文档一直“正在加载数据”）。
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(new URL(`../src/legal/${path}`, import.meta.url), "utf8");

test("线索分页用自己的请求序号，不动打开详情的序号", () => {
  const queries = read("services/queriesActions.tsx");
  const start = queries.indexOf("const loadCounselDetailCluesPage");
  const body = queries.slice(start, queries.indexOf("const openRelatedCustomer", start));
  assert.match(body, /\+\+counselDetailCluePageRequestRef\.current/);
  assert.doesNotMatch(body, /counselDetailClueRequestRef/);
  assert.match(body, /currentCaseId: counselDetailCaseIdRef\.current/);
});

test("只有打开详情时递增 counselDetailClueRequestRef", () => {
  const files = ["services/queriesActions.tsx", "services/workflowActions.tsx", "CaseCenterPage.tsx"].map(read).join("\n");
  assert.equal((files.match(/\+\+counselDetailClueRequestRef\.current/g) || []).length, 1);
  assert.match(read("CaseCenterPage.tsx"), /get counselDetailCluePageRequestRef\(\) \{ return counselDetailCluePageRequestRef; \}/);
});
