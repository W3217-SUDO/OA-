import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("customer detail contacts tab keeps the legacy create-contact entry", () => {
  const detailContactsTabStart = source.indexOf('className="customer-view-tabs"');
  const detailNotesTabStart = source.indexOf('key: "notes"', detailContactsTabStart);
  assert.ok(detailContactsTabStart >= 0 && detailNotesTabStart > detailContactsTabStart);

  const detailContactsTab = source.slice(detailContactsTabStart, detailNotesTabStart);
  assert.match(detailContactsTab, /canManageCurrentCustomer\s*&&/);
  assert.match(detailContactsTab, /onClick=\{\(\) => openNewEditor\("contact"\)\}/);
  assert.match(detailContactsTab, />新建联系人<\/Button>/);
});
