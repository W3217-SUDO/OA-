import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("ordinary case detail exposes the assisted-fee lifecycle through its dedicated API", () => {
  assert.match(source, /key:"assisted-fees",label:"资助费用"/);
  assert.match(source, /`\/cases\/\$\{caseId\}\/assisted-fees`/);
  assert.match(source, /api\.post\(`\/cases\/\$\{viewingCounselCase\.id\}\/assisted-fees`, payload\)/);
  assert.match(source, /api\.put\(`\/cases\/\$\{viewingCounselCase\.id\}\/assisted-fees\/\$\{assistedFeeEditor\.id\}`, payload\)/);
  assert.match(source, /\/assisted-fees\/\$\{assistedFeeConfirming\.id\}\/confirm/);
  assert.match(source, /api\.delete\(`\/cases\/\$\{viewingCounselCase\.id\}\/assisted-fees\/\$\{row\.id\}`\)/);
});

test("assisted fee allows an omitted amount and only permits pending rows to mutate", () => {
  assert.match(source, /amount\?: number \| null/);
  assert.match(source, /values\.amount === undefined \|\| values\.amount === null/);
  assert.match(source, /assistedFeeEditor\s*\? \{ amount: values\.amount === undefined \|\| values\.amount === null \? null/);
  for (const action of ["修改", "办理确认", "删除"]) {
    assert.match(source, new RegExp(`row\\.status === "待办理" && counselDetailCapabilities\\.can_manage_assisted_fees[\\s\\S]{0,500}${action}`));
  }
});

test("assisted fee loading guards against a stale case-switch response", () => {
  assert.match(source, /counselDetailCaseIdRef\.current !== caseId/);
  assert.match(source, /counselDetailAssistedFeeRequestRef/);
});
