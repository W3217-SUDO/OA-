import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { buildCaseOrdinarySearchPayload, ordinaryCaseQueueForView } from "./src/caseOrdinarySearchParity.mjs";


test("9.2 row 5 preserves the supplement-opinion queue in the drilldown request", () => {
  const queue = ordinaryCaseQueueForView("case-company-supplement-opinion");
  assert.equal(queue, "supplement_opinion");
  assert.equal(
    buildCaseOrdinarySearchPayload({ case_queue: queue }, "company", [], 1, 15).case_queue,
    "supplement_opinion",
  );
  assert.equal(ordinaryCaseQueueForView("case-company"), "");
});

test("9.2 row 5 exposes a dedicated supplement-opinion workspace label", () => {
  const source = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
  assert.match(source, /"case-company-supplement-opinion": "补充意见"/);
});
