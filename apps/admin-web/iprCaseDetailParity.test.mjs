import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const helper = await import(new URL("./src/iprCaseDetailParity.mjs", import.meta.url));
const page = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

test("IPR customer payload requires a selected customer and selected primary", () => {
  assert.equal(helper.getIprCaseCustomerValidationError({ customerIds: [], primaryCustomerId: null }), "请至少选择一个客户并指定主客户");
  assert.equal(helper.getIprCaseCustomerValidationError({ customerIds: [3, 3], primaryCustomerId: 9 }), "请从已选客户中指定一个主客户");
  assert.equal(helper.getIprCaseCustomerValidationError({ customerIds: [3, 3], primaryCustomerId: 3 }), "");
  assert.deepEqual(helper.buildIprCaseCustomerPayload({ customerIds: [3, 3, 7], primaryCustomerId: 3 }), { customer_ids: [3, 7], primary_customer_id: 3 });
});

test("IPR contact and law-firm payloads trim and deduplicate selections", () => {
  assert.deepEqual(helper.buildIprCaseContactPayload({ customerId: 7, documentContactIds: [" c1 ", "c1", ""], technologyContactIds: ["t1", " t1 "] }), {
    customer_id: 7,
    document_contact_ids: ["c1"],
    technology_contact_ids: ["t1"],
  });
  assert.deepEqual(helper.buildIprCaseLawFirmPayload({ lawFirmIds: [5, 5, 2] }), { law_firm_ids: [5, 2] });
});

test("IPR destructive actions expose distinct confirmation copy", () => {
  for (const kind of ["log", "file", "reminder", "assisted-fee"]) {
    const prompt = helper.getIprCaseDeletionConfirmation(kind, "示例");
    assert.equal(prompt.okText, "确认删除");
    assert.equal(prompt.cancelText, "取消");
    assert.match(prompt.title, /删除/);
    assert.match(prompt.content, /示例/);
  }
  assert.match(page, /getIprCaseDeletionConfirmation/);
  assert.match(page, /buildIprCaseCustomerPayload/);
  assert.match(page, /buildIprCaseContactPayload/);
  assert.match(page, /buildIprCaseLawFirmPayload/);
});
