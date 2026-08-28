import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { FEE_SUBTYPE_TO_TYPE, LEGACY_OTHER_FEE_SUBTYPES } from "./src/caseRelationConsumption.mjs";

const page = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 13 restores the exact legacy other fee choices", () => {
  assert.deepEqual(LEGACY_OTHER_FEE_SUBTYPES, ["\u6848\u6e90\u4ecb\u7ecd\u8d39", "\u6743\u5229\u4eba\u8d54\u507f\u6b3e", "\u6295\u8d44\u4eba\u5206\u6210", "\u5176\u4ed6\u8d39\u7528"]);
  for (const subtype of LEGACY_OTHER_FEE_SUBTYPES) assert.equal(FEE_SUBTYPE_TO_TYPE[subtype], "\u5176\u4ed6\u8d39\u7528");
});

test("row 13 opens other creation without a generic preselection", () => {
  assert.match(page, /feeSubtypePreset === "other"[\s\S]*?LEGACY_OTHER_FEE_SUBTYPES/);
  assert.match(page, /const otherPreset = expenseSubtype === "\u5176\u4ed6\u8d39\u7528"/);
  assert.match(page, /officialPreset \|\| thirdPartyPreset \|\| agencyPreset \|\| otherPreset \? undefined/);
});
