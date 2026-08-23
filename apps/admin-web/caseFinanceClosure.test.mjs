import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const casePage = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const financePage = fs.readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");
const navigation = fs.readFileSync(new URL("./src/businessRecordDetailNavigation.ts", import.meta.url), "utf8");

test("law-firm payment uses the ordinary payment request flow", () => {
  assert.match(casePage, /const openPaymentRequest = \(row: CaseRow\) =>/);
  assert.match(casePage, /const submitPaymentRequest = async \(\) =>/);
  assert.match(casePage, /api\.post\(`\/finance\/fees\/\$\{paymentRequestFee\.id\}\/submit`/);
  assert.match(casePage, /if\(key==="payment"\)return openPaymentRequest\(selectedFirmFee!\)/);
  assert.doesNotMatch(casePage, /if\(key==="payment"\)return void previewInternalPayment\(selectedFirmFee!\)/);
});

test("case fee invoice and refund keep the selected fee context", () => {
  assert.match(navigation, /"create_invoice" \| "create_refund"/);
  assert.match(casePage, /action:key==="invoice"\?"create_invoice":"create_refund"/);
  assert.match(casePage, /key==="invoice"\?"finance-invoice-mine":"finance-refund"/);
  assert.match(financePage, /target\.action === "create_invoice"/);
  assert.match(financePage, /target\.action === "create_refund"/);
  assert.match(financePage, /case_fee_ids: \[sourceFee\.id\]/);
  assert.match(financePage, /fee_record_id: data\.id/);
});

test("case task and internal settlement tables preserve key status fields", () => {
  assert.equal((casePage.match(/dataIndex:\s*"priority"/g) || []).length, 3);
  assert.match(casePage, /row\.data\.payment_requested_amount/);
  assert.match(casePage, /row\.data\.paid_amount/);
});
