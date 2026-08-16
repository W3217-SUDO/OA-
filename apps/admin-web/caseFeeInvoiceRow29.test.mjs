import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 29 blocks a second case-fee invoice application before opening the form", () => {
  assert.match(source, /\["已申请","已开票"\]\.includes\(String\(selectedFirmFee!\.data\.invoice_status\|\|""\)\)/);
  assert.match(source, /不能重复申请开票/);
  assert.match(source, /action:key==="invoice"\?"create_invoice":"create_refund"/);
});
