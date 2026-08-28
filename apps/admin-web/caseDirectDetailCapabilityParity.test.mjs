import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("directly opened migrated cases use the detail capability response", () => {
  assert.match(
    source,
    /const getCaseCapability = \(row\?: CaseRow \| null\) => \{[\s\S]*?if \(viewingCounselCase\?\.id === row\.id\) return counselDetailCapabilities;[\s\S]*?return caseActionCapabilities\[row\.id\] \|\| noCaseDetailWriteCapability;/,
  );
});

test("detail fee and task actions use the shared effective capability resolver", () => {
  assert.match(source, /const openCaseFee = \(row: CaseRow,[\s\S]*?if \(!getCaseCapability\(row\)\.can_create_finance\)/);
  assert.match(source, /const openCaseTaskCreator = \(row: CaseRow\) => \{[\s\S]*?if \(!getCaseCapability\(row\)\.can_create_case_task\)/);
  assert.match(source, /const openCustomerTaskCreator = \(row: CaseRow\) => \{[\s\S]*?if \(!getCaseCapability\(row\)\.can_create_case_task\)/);
});
