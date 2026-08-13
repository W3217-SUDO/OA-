import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 28 opens a payment request form with amount and payment account", () => {
  assert.match(source, /const \[paymentRequestFee, setPaymentRequestFee\]/);
  assert.match(source, /const \[paymentRequestForm\] = Form\.useForm\(\)/);
  assert.match(source, /label=\"申请付款金额\" name=\"amount\"/);
  assert.match(source, /label=\"付款账号\" name=\"payment_account\"/);
  assert.match(source, /payment_account: String\(values\.payment_account/);
  assert.match(source, /payment_requested_amount/);
  assert.match(source, /\["草稿", "已退回", "已审批", "部分付款"\]\.includes\(row\.status\)/);
});

test("row 28 keeps the selected fee linked to the payment request", () => {
  assert.match(source, /api\.post\(`\/finance\/fees\/\$\{paymentRequestFee\.id\}\/submit`/);
  assert.match(source, /row\.data\.amount/);
  assert.match(source, /title:\"付款账号\"/);
});
