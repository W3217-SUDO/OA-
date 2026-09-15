import test from "node:test";
import assert from "node:assert/strict";

import { caseFeeRefundLabel } from "./src/caseFeeLegacyProjection.mjs";

test("9.1 row 3 shows the legacy refund amount and progress independently", () => {
  assert.equal(caseFeeRefundLabel({ refund_amount: 0, refunded_amount: 0 }), "0");
  assert.equal(caseFeeRefundLabel({ refund_amount: 200, refunded_amount: 80 }), "120 (未退)");
  assert.equal(caseFeeRefundLabel({ refund_requested_amount: 200, refunded_amount: 200 }), "200 (已退)");
  assert.equal(caseFeeRefundLabel({ refund_status: "R100", refund_amount: 200 }), "不再办理退费");
  assert.equal(caseFeeRefundLabel({ refund_not_required: true }), "不再办理退费");
});

test("9.15 court refunds show remaining balance and ignore ordinary receipt totals", () => {
  assert.equal(caseFeeRefundLabel({refund_amount:50, received_amount:100}), "50 (未退)");
  assert.equal(caseFeeRefundLabel({refund_amount:50, refunded_amount:30}), "20 (未退)");
  assert.equal(caseFeeRefundLabel({refund_amount:50, refunded_amount:50}), "50 (已退)");
  assert.equal(caseFeeRefundLabel({refund_amount:50, refunded_amount:0}), "50 (未退)");
});
