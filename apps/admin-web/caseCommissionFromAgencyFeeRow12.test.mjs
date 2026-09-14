import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/legal/CaseCenterPage.tsx", import.meta.url), "utf8");
const panel = readFileSync(new URL("./src/legal/CaseDetail/CaseFeesPanel.tsx", import.meta.url), "utf8");
const actions = readFileSync(new URL("./src/legal/services/financeActions.tsx", import.meta.url), "utf8");
const modalStart = source.indexOf('title="新增提成"');
const modalEnd = source.indexOf('open={Boolean(paymentPackagePreview)}', modalStart);
const modal = source.slice(modalStart, modalEnd);

test("row 12 opens the dedicated commission preview instead of the generic fee drawer", () => {
  assert.match(panel, /key === "commission" \? void openCaseCommission\?\.\(\)/);
  assert.match(actions, /\/commission-preview/);
  assert.doesNotMatch(panel, /key==="commission"\?handleInternalFeeAction\("create"\)/);
});

test("migrated lawyer agency fee subtype is accepted even when the base fee type is generic", () => {
  assert.match(actions, /selectedFirmFee!\.data\.expense_subtype/);
  assert.match(actions, /selectedFirmFee!\.data\.fee_type/);
  assert.match(actions, /feeTypes\.some\(\(feeType\) => feeType\.includes\("代理费"\)\)/);
});

test("row 33 uses the legacy 700px right-side commission workspace and compact table", () => {
  assert.match(modal, /placement="right"/);
  assert.match(modal, /width=\{700\}/);
  assert.match(modal, /case-commission-drawer/);
  assert.match(modal, /tableLayout="fixed"/);
  assert.match(modal, /case-commission-key-input/);
  for (const heading of ["案号", "费用类型", "支付对象", "基数", "参考提成", "实际金额", "备注", "操作"]) {
    assert.match(modal, new RegExp(heading));
  }
  for (const syncField of ["commission_type", "base_amount", "actual_amount", "remark"]) {
    assert.match(modal, new RegExp(`syncFirstCommissionField\\(\"${syncField}\"\\)`));
  }
  assert.match(modal, /品管人员/);
  assert.match(modal, /quality_manager_source/);
  assert.match(modal, /未配置对应提成/);
});

test("row 12 submits one atomic batch and refreshes internal settlement", () => {
  assert.match(actions, /api\.post\(`\/cases\/\$\{viewingCounselCase\.id\}\/commissions`/);
  assert.match(actions, /source_fee_id: caseCommissionPreview\.source_fee\.id/);
  assert.match(actions, /preview_key: row\.preview_key/);
  assert.match(actions, /base_amount: row\.base_amount/);
  assert.match(actions, /openCounselDetail\(viewingCounselCase, "internal-fees"\)/);
  for (const heading of ["申请单号", "收款人", "提成类型", "金额", "案号", "申请日期"]) {
    assert.match(modal, new RegExp(heading));
  }
});
