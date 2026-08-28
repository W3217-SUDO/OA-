import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  FEE_SUBTYPE_TO_TYPE,
  LEGACY_OFFICIAL_FEE_SUBTYPES,
} from "./src/caseRelationConsumption.mjs";

const page = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const expected = [
  "一审诉讼费", "二审诉讼费", "再审诉讼费", "公证费", "调解金额",
  "判决金额", "保全费", "执行费", "核定成本",
];

test("row 7 restores the legacy official fee type list in exact order", () => {
  assert.deepEqual(LEGACY_OFFICIAL_FEE_SUBTYPES, expected);
  for (const subtype of expected) assert.equal(FEE_SUBTYPE_TO_TYPE[subtype], "官方费用");
});

test("row 7 official entry bypasses missing file-type relation configuration", () => {
  assert.match(page, /feeSubtypePreset === "official"\s*\? LEGACY_OFFICIAL_FEE_SUBTYPES/);
  assert.match(page, /const officialPreset = expenseSubtype === "官费"/);
  assert.match(page, /openCaseFee\(viewingCounselCase,scope,subtype\)/);
});
