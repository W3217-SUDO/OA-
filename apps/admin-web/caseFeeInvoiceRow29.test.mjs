import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 29 blocks a second case-fee invoice application before opening the form", () => {
  assert.match(source, /api\.get\("\/finance\/case-fees\/invoice-status"/);
  assert.match(source, /invoice_status:"未开票"/);
  assert.match(source, /resolveCaseFeeInvoiceEligibility\(selectedFirmFee!\.id/);
  assert.match(source, /if\(!eligibility\.ok\)\{message\.warning\(eligibility\.error\);return;\}/);
  assert.match(source, /action:key==="invoice"\?"create_invoice":"create_refund"/);
});
