import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { buildCasePaymentTypeSelectOptions, buildExternalPaymentRequestPayload } from "./src/casePaymentUnitParity.mjs";

test("payment unit options expose payee, bank and account for keyword selection", () => {
  assert.deepEqual(buildCasePaymentTypeSelectOptions([{ id: 14, payee: "第14行收款单位", account_bank: "第14行银行", account: "R14-ACCOUNT" }]), [
    { value: 14, label: "第14行收款单位｜第14行银行｜R14-ACCOUNT" },
  ]);
});
test("external payment submits a master-data id instead of free-text payee fields", () => {
  assert.deepEqual(buildExternalPaymentRequestPayload({ amount: 140, payment_type_id: 14, payment_remark: "第14行付款" }, "fallback"), {
    amount: 140, payment_type_id: 14, payment_remark: "第14行付款", comment: "第14行付款",
  });
});

test("case payment UI contains legacy payment-unit creation and removes direct payee inputs", () => {
  const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
  assert.match(source, /title="新增付款单位"/);
  assert.match(source, /label="性质"/);
  assert.match(source, /label="收款单位"/);
  assert.match(source, /label="开户行"/);
  assert.match(source, /label="账号信息"/);
  assert.match(source, /name="payment_type_id"/);
  assert.doesNotMatch(source, /name="payment_payee"/);
});
