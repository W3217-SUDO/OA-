import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/finance/FinanceCenterView.tsx", import.meta.url), "utf8");
const actions = readFileSync(new URL("./src/finance/services/paymentsActions.tsx", import.meta.url), "utf8");
const caseSource = readFileSync(new URL("./src/legal/CaseCenterPage.tsx", import.meta.url), "utf8");
const casePanel = readFileSync(new URL("./src/legal/CaseDetail/CaseFeesPanel.tsx", import.meta.url), "utf8");

test("ordinary agency fee forms do not embed employee commission editing", () => {
  assert.doesNotMatch(source, /FeeCommissionEditor/);
  assert.doesNotMatch(caseSource, /FeeCommissionEditor/);
});

test("ordinary finance fee writes strip obsolete embedded commission fields", () => {
  assert.match(actions, /const \{ commission_mode, commission_details, \.\.\.payload \} = v/);
  assert.doesNotMatch(actions, /commission_mode: v\.commission_mode/);
});

test("employee commission remains a dedicated action for a selected agency fee", () => {
  assert.match(casePanel, /新建提成\(选择代理费\)/);
  assert.match(casePanel, /openCaseCommission/);
  assert.match(caseSource, /title="新增提成"/);
  assert.match(caseSource, /aria-label="新增提成行"/);
});
