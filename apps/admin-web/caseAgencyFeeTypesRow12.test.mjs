import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { FEE_SUBTYPE_TO_TYPE, LEGACY_AGENCY_FEE_SUBTYPES } from "./src/caseRelationConsumption.mjs";

const page = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 12 restores the exact legacy agency fee choices", () => {
  assert.deepEqual(LEGACY_AGENCY_FEE_SUBTYPES, ["律师代理费", "律师咨询费", "律师培训费", "律师见证费"]);
  for (const subtype of LEGACY_AGENCY_FEE_SUBTYPES) assert.equal(FEE_SUBTYPE_TO_TYPE[subtype], "代理费");
});

test("row 12 opens agency creation without a generic preselection", () => {
  assert.match(page, /feeSubtypePreset === "agency"[\s\S]*?LEGACY_AGENCY_FEE_SUBTYPES/);
  assert.match(page, /const agencyPreset = expenseSubtype === "代理费"/);
  assert.match(page, /officialPreset \|\| thirdPartyPreset \|\| agencyPreset \|\| otherPreset \? undefined/);
});
