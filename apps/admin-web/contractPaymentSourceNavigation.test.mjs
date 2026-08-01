import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract payment records expose an exact finance target query", () => {
  assert.match(source, /const openRelatedPayment = \(payment: Contract\)/);
  assert.match(source, /params\.set\("page", "finance-payment-mine"\)/);
  assert.match(source, /params\.set\("payment_no", paymentNo\)/);
  assert.match(source, /onNavigate\?\.\("finance-payment-mine"\)/);
  assert.match(source, /dataSource=\{detailPayments\}/);
  assert.match(source, /openRelatedPayment\(row\)/);
});
