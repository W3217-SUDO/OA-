// 501384（fwl 11-04）：费用新建后还没产生数据时本案人员都能改删；有了审批、付款、退费、回款、开票、结算后只有分配了权限的角色能改删。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const source = fs.readFileSync(new URL("../src/legal/caseFeeMemberEdit.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const module = { exports: {} };
new Function("exports", "require", "module", compiled)(module.exports, () => ({}), module);
const { caseFeeUntouched, canChangeCaseFee } = module.exports;

test("没产生数据的费用本案人员能改删，有数据后要角色权限", () => {
  const fresh = { status: "草稿", data: { amount: 100 } };
  const imported = { status: "已记录", data: { amount: 100, payment_requested_amount: 0 } };
  assert.ok(caseFeeUntouched(fresh) && caseFeeUntouched(imported));
  for (const touched of [
    { status: "待审批", data: {} }, { status: "草稿", data: { payment_requested_amount: 50 } }, { status: "草稿", data: { cashed_amount: 1 } },
    { status: "草稿", data: { invoice_no: "123" } }, { status: "草稿", data: { refund_requested_amount: 10 } }, { status: "草稿", data: { receipt_files: [{ id: 1 }] } },
  ]) assert.ok(!caseFeeUntouched(touched), JSON.stringify(touched));
  const member = { can_edit_finance: false, can_delete_finance: false, can_change_untouched_finance: true };
  assert.ok(canChangeCaseFee(member, "edit", fresh) && canChangeCaseFee(member, "delete", fresh));
  assert.ok(!canChangeCaseFee(member, "edit", { status: "已付款", data: {} }));
  const outsider = { can_edit_finance: false, can_delete_finance: false, can_change_untouched_finance: false };
  assert.ok(!canChangeCaseFee(outsider, "edit", fresh));
  assert.ok(canChangeCaseFee({ ...outsider, can_edit_finance: true }, "edit", { status: "已付款", data: {} }), "有角色权限照旧");
});
