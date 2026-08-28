import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { FEE_SUBTYPE_TO_TYPE, LEGACY_THIRD_PARTY_FEE_SUBTYPES } from "./src/caseRelationConsumption.mjs";

const page = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 11 restores the exact legacy third-party fee choices", () => {
  assert.deepEqual(LEGACY_THIRD_PARTY_FEE_SUBTYPES, ["检索费", "公告费", "担保费", "鉴定费", "公证服务费"]);
  for (const subtype of LEGACY_THIRD_PARTY_FEE_SUBTYPES) assert.equal(FEE_SUBTYPE_TO_TYPE[subtype], "其他费用");
});

test("row 11 opens third-party creation without a preselected generic value", () => {
  assert.match(page, /useState<"official" \| "third-party" \| "agency" \| "other" \| "">/);
  assert.match(page, /feeSubtypePreset === "third-party"[\s\S]*?LEGACY_THIRD_PARTY_FEE_SUBTYPES/);
  assert.match(page, /const thirdPartyPreset = expenseSubtype === "第三方费用"/);
  assert.match(page, /officialPreset \|\| thirdPartyPreset \|\| agencyPreset \|\| otherPreset \? undefined/);
});
