// 财务编辑、删除（2026-10-28）：勾选页面自动带出对应动作，“我的…”个人页面不带；与后端对应关系一致。
import assert from "node:assert/strict";
import test from "node:test";

const { pageFinanceActions, FINANCE_ACTION_KEYS } = await import("../src/system/financeActions.ts");

test("勾选财务页面带出该页的编辑、删除", () => {
  assert.deepEqual(pageFinanceActions(["finance-receipts-icbc"]), ["finance.receipt.update", "finance.receipt.delete"]);
  assert.deepEqual(pageFinanceActions(["finance-payment-writeoff", "finance-fee-query"]),
    ["finance.payment.update", "finance.payment.delete", "finance.fee.update", "finance.fee.delete"]);
  assert.deepEqual(pageFinanceActions(["finance-payment-mine", "finance-invoice-mine", "finance-internal-audit", "case-mine"]), []);
  assert.equal(FINANCE_ACTION_KEYS.length, 6);
});
