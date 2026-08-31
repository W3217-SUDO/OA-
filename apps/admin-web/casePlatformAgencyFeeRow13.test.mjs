import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  FEE_SUBTYPE_TO_TYPE,
  LEGACY_AGENCY_FEE_SUBTYPES,
  PLATFORM_AGENCY_FEE_SUBTYPE,
  agencyFeeSubtypesForScope,
  normalizeFeeSubtypeForScope,
} from "./src/caseRelationConsumption.mjs";

const page = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("8.31 row 13 keeps platform agency fee distinct from law-firm agency fee", () => {
  assert.equal(PLATFORM_AGENCY_FEE_SUBTYPE, "平台代理费");
  assert.deepEqual(agencyFeeSubtypesForScope("平台"), ["平台代理费"]);
  assert.deepEqual(agencyFeeSubtypesForScope("律所"), LEGACY_AGENCY_FEE_SUBTYPES);
  assert.equal(FEE_SUBTYPE_TO_TYPE["平台代理费"], "代理费");
});

test("8.31 row 13 normalizes every platform agency entry and historical draft", () => {
  assert.equal(normalizeFeeSubtypeForScope("平台", "代理费"), "平台代理费");
  assert.equal(normalizeFeeSubtypeForScope("律所", "代理费"), "代理费");
  assert.match(page, /normalizeFeeSubtypeForScope\(scope, "代理费"\)/);
  assert.match(page, /agencyFeeSubtypesForScope\(activeFeeContractScope\)/);
  assert.match(page, /expenseScope === "平台" && agencyPreset[\s\S]*?PLATFORM_AGENCY_FEE_SUBTYPE/);
  assert.match(page, /const expenseSubtype = normalizeFeeSubtypeForScope\(expenseScope, row\.data\.expense_subtype/);
});

test("8.31 row 13 retains the old-system command label at all platform entry points", () => {
  assert.match(page, /key: "platform-代理费", label: "新增代理费"/);
  assert.match(page, /renderCaseFeeEmptyState\("平台"\)/);
  assert.match(page, /openCaseFeeBySubtype\("平台",key\)/);
});
