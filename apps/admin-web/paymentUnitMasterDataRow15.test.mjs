import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const systemCenter = readFileSync(new URL("./src/SystemCenterPage.tsx", import.meta.url), "utf8");
const contractCenter = readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("row 15 system parameters reproduce the legacy payment-unit vocabulary", () => {
  assert.match(systemCenter, /payment_type: "付款单位名称"/);
  assert.match(systemCenter, /title: "付款单位名"/);
  assert.match(systemCenter, /\? "新增付款单位"/);
  assert.match(systemCenter, /新增"\}付款单位/);
});

test("row 15 payment-unit editor contains exactly the four legacy business fields", () => {
  const start = systemCenter.indexOf('{category === "payment_type" ? (');
  const end = systemCenter.indexOf("          ) : (", start);
  const editor = systemCenter.slice(start, end);
  for (const label of ["性质", "收款单位", "开户行", "账号信息"]) {
    assert.match(editor, new RegExp(`label="${label}"`));
  }
  assert.doesNotMatch(editor, /label="代码"|label="名称"|label="排序"|label="启用"/);
});

test("row 15 contract payment selects and creates shared master data by id", () => {
  assert.match(contractCenter, /name="payment_type_id"/);
  assert.match(contractCenter, /\/contracts\/\$\{paymentTarget\.id\}\/payment-types/);
  assert.match(contractCenter, /title="新增付款单位"/);
  assert.match(contractCenter, /selectedContractPaymentType\.account_bank/);
  const formStart = contractCenter.indexOf('<Form form={paymentForm} layout="vertical">');
  const formEnd = contractCenter.indexOf("</Form>", formStart);
  const paymentForm = contractCenter.slice(formStart, formEnd);
  assert.doesNotMatch(paymentForm, /name="payee"|name="account"/);
});
