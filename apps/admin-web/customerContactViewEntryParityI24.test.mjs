import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("customer detail contacts retain the legacy view-contact entry", () => {
  const detailContactsStart = source.indexOf('className="customer-view-tabs"');
  const detailContractsStart = source.indexOf('key: "contracts"', detailContactsStart);
  assert.ok(detailContactsStart >= 0 && detailContractsStart > detailContactsStart);

  const contactsSection = source.slice(detailContactsStart, detailContractsStart);
  assert.match(source, /\[viewingContact, setViewingContact\] = useState<Contact \| null>\(null\)/);
  assert.match(contactsSection, /onClick=\{\(\)\s*=>\s*setViewingContact\(row\)\}/);
  assert.match(contactsSection, />查看<\/Button>/);
  assert.match(source, /open=\{Boolean\(viewingContact\)\}/);
});
