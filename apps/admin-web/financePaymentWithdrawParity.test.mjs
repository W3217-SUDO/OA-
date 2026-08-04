import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);

test("my payment and internal-fee rows expose the existing guarded withdraw flow", () => {
  const internalOperation = source.match(
    /const internalMineOperation = \([\s\S]*?\n  const feeQueryFields/,
  );
  const paymentOperation = source.match(
    /const originalOperation = \([\s\S]*?\n  const openGeneralSettlementReview/,
  );

  assert.ok(internalOperation, "internal-fee row operation should exist");
  assert.ok(paymentOperation, "payment row operation should exist");
  assert.match(
    source,
    /const canWithdrawFinanceFee = \(row: Fee\) =>[\s\S]*?\["草稿", "待审批", "已审批", "待付款"\]\.includes\(row\.status\)[\s\S]*?\(canManage \|\| row\.owner === currentUser\.username\)/,
  );
  assert.match(
    internalOperation[0],
    /canWithdrawFinanceFee\(row\)[\s\S]*?row\.data\.fee_type === "内部费用"[\s\S]*?openPaymentCancel\(row\)[\s\S]*?撤回/,
  );
  assert.match(
    paymentOperation[0],
    /initialView === "finance-payment-mine"[\s\S]*?canWithdrawFinanceFee\(row\)[\s\S]*?openPaymentCancel\(row\)[\s\S]*?撤回请款/,
  );
  assert.match(
    source,
    /open=\{Boolean\(paymentCancelTarget\)\}[\s\S]*?onOk=\{\(\) => void submitPaymentCancel\(\)\}/,
  );
  assert.match(
    source,
    /api\.post\(`\/finance\/fees\/\$\{paymentCancelTarget\.id\}\/cancel`, \{\s*reason,\s*\}\)[\s\S]*?refreshCurrentFinanceFeeList\(\{[\s\S]*?paymentCancelTarget\.status/,
  );
});
