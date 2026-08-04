import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("customer detail tabs refresh the persisted detail when switching legacy child views", () => {
  assert.match(source, /const handleCustomerDetailTabChange = \(key: string\) => \{/);
  assert.match(source, /if \(contacts && key !== detailTab\) void refreshDetail\(contacts\);/);
  assert.equal((source.match(/onChange=\{handleCustomerDetailTabChange\}/g) || []).length, 2);
});
