// 财务编辑、删除（2026-10-28）：只有回款管理、付款打包-管理、请款单审批带出动作；与后端对应关系一致。
import assert from "node:assert/strict";
import test from "node:test";

const { pageFinanceActions, FINANCE_ACTION_KEYS } = await import("../src/system/financeActions.ts");

test("只有管理页面带出编辑、删除", () => {
  assert.deepEqual(pageFinanceActions(["finance-receipts-manage"]), ["finance.receipt.update", "finance.receipt.delete"]);
  assert.deepEqual(pageFinanceActions(["finance-payment-package-manage", "finance-payment-audit"]),
    ["finance.payment.update", "finance.payment.delete", "finance.fee.update", "finance.fee.delete"]);
  // 律师能看的页面不带。
  assert.deepEqual(pageFinanceActions(["finance-receipts-claim", "finance-receipts-pending", "finance-receipts-allocated",
    "finance-receipts-query", "finance-receipts-icbc", "finance-payment-query", "finance-payment-writeoff",
    "finance-fee-query", "finance-payment-mine"]), []);
  assert.equal(FINANCE_ACTION_KEYS.length, 6);
});
