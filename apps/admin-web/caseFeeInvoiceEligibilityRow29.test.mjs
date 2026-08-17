import test from "node:test";
import assert from "node:assert/strict";

import { resolveCaseFeeInvoiceEligibility } from "./src/caseFeeInvoiceEligibility.mjs";

test("selected uninvoiced fee can enter invoice application", () => {
  const fee = { id: 29, data: { invoice_status: "未开票" } };
  assert.deepEqual(resolveCaseFeeInvoiceEligibility(29, [fee]), { ok: true, fee });
});

test("fee absent from uninvoiced candidates is blocked before navigation", () => {
  assert.deepEqual(resolveCaseFeeInvoiceEligibility(29, []), {
    ok: false,
    error: "该费用已经申请开票或当前不可开票，不能重复申请",
  });
});
