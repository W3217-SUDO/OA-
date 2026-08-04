import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("customer list keeps the legacy direct communication entry within existing scopes", () => {
  assert.match(source, /const canOpenCustomerCommunication = \[/);
  assert.match(source, /"customer-mine"/);
  assert.match(source, /"customer-shared"/);

  const communicationStart = source.indexOf('key: "communication"');
  const contactCountStart = source.indexOf('key: "contactCount"');
  assert.ok(communicationStart >= 0 && contactCountStart > communicationStart);

  const communicationColumn = source.slice(communicationStart, contactCountStart);
  assert.match(communicationColumn, /canOpenCustomerCommunication/);
  assert.match(communicationColumn, /onClick=\{\(\) => openCustomerCommunication\(r\)\}/);
  assert.match(communicationColumn, />\s*新增沟通记录\s*<\/Button>/);
});
