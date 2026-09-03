import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { buildCaseOrdinarySearchPayload, ordinaryCaseQueueForView } from "./src/caseOrdinarySearchParity.mjs";


test("9.2 row 6 preserves the urgent queue in the drilldown request", () => {
  const queue = ordinaryCaseQueueForView("case-company-urgent");
  assert.equal(queue, "urgent");
  assert.equal(buildCaseOrdinarySearchPayload({ case_queue: queue }, "company", [], 1, 15).case_queue, "urgent");
});

test("9.2 row 6 renders server-projected phase change time and duration", () => {
  const caseSource = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
  const appSource = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
  assert.match(caseSource, /变更时间:\{row\.data\.phase_changed_at \|\| ""\}/);
  assert.match(caseSource, /row\.data\.phase_duration \|\| row\.data\.phase_changed_days/);
  assert.match(appSource, /"case-company-urgent": "紧急案件"/);
});
