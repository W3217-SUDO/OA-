import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const financePage = fs.readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");
const createPage = fs.readFileSync(new URL("./src/PlatformFinancePage.tsx", import.meta.url), "utf8");

test("row 5 claim dialog searches the complete system-customer source", () => {
  assert.match(financePage, /api\.get\("\/finance\/customer-options", \{\s*params: \{ keyword \}/);
  assert.match(financePage, /onSearch=\{\(keyword\) => void searchClaimCustomers\(keyword\)\}/);
  assert.match(financePage, /options=\{claimCustomers\.map/);
  assert.match(financePage, /filterOption=\{false\}/);
});

test("row 5 never substitutes the receipt number for a missing bank reference", () => {
  assert.match(createPage, /bank_reference: values\.bankReference\?\.trim\(\) \|\| ""/);
  assert.doesNotMatch(createPage, /bank_reference: values\.bankReference\?\.trim\(\) \|\| receiptNo/);
});
