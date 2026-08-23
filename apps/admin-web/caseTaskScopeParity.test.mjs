import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case and customer task tabs use independent scoped paging", () => {
  assert.match(source, /scope: "case"/);
  assert.match(source, /scope: "customer"/);
  assert.match(source, /counselDetailCustomerTasks/);
  assert.match(source, /counselDetailCustomerTaskPagination/);
  assert.doesNotMatch(source, /dataSource=\{counselDetailTasks\.filter\(row=>row\.source==="客户任务"\)\}/);
});
