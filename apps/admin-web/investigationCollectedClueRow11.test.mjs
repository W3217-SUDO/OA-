import assert from "node:assert/strict";
import test from "node:test";

import {
  COLLECTED_CLUE_STATUSES,
  clueCaseNo,
  clueInvestigatorSearchText,
} from "./src/investigationCollectedClueParity.mjs";

test("collected clue routes retain clues after case conversion", () => {
  assert.deepEqual([...COLLECTED_CLUE_STATUSES], ["已取证", "已转案件"]);
});

test("investigator search covers account and Chinese display name", () => {
  const searchText = clueInvestigatorSearchText(
    {
      owner: "taowei",
      owner_display_name: "陶威",
      data: { investigator: "taowei", investigator_display_name: "陶威" },
    },
    "陶威",
  );
  assert.match(searchText, /taowei/);
  assert.match(searchText, /陶威/);
});

test("case number prefers the linked case and falls back to converted case", () => {
  assert.equal(clueCaseNo({ data: { converted_case_no: "SHMS2600999" } }), "SHMS2600999");
  assert.equal(
    clueCaseNo({ data: { case_no: "SHMS2600888", converted_case_no: "SHMS2600999" } }),
    "SHMS2600888",
  );
});
