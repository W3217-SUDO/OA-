import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 28 opens the legacy payment-request step", () => {
  assert.match(source, /const \[paymentRequestFee, setPaymentRequestFee\]/);
  assert.match(source, /const \[paymentRequestForm\] = Form\.useForm\(\)/);
  assert.match(source, /<Steps size="small" current=\{1\}/);
  assert.match(source, /case-fee-payment-request-table/);
  assert.match(source, /name="amount"/);
  assert.match(source, /name="payment_remark"/);
  assert.match(source, /name="payment_payee"/);
  assert.match(source, /name="payment_account"/);
});

test("row 28 keeps the selected fee and payment fields linked to submit", () => {
  assert.match(source, /if\(key==="payment"\)return openPaymentRequest\(selectedFirmFee!\);/);
  assert.match(source, /api\.post\(`\/finance\/fees\/\$\{paymentRequestFee\.id\}\/submit`/);
  assert.match(source, /payment_remark: String\(values\.payment_remark/);
  assert.match(source, /payment_payee: String\(values\.payment_payee/);
  assert.match(source, /payment_account: String\(values\.payment_account/);
  assert.match(source, /payment_requested_amount/);
  assert.match(source, /\["草稿", "已退回", "已审批", "部分付款"\]\.includes\(row\.status\)/);
});
