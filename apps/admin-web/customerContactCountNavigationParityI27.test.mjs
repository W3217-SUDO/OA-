import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("customer contact count keeps the legacy contact-management jump", () => {
  const contactCountStart = source.indexOf('key: "contactCount"');
  const contractCountStart = source.indexOf('key: "contractCount"', contactCountStart);
  assert.ok(contactCountStart >= 0 && contractCountStart > contactCountStart);

  const contactCountColumn = source.slice(contactCountStart, contractCountStart);
  assert.match(contactCountColumn, /<Button/);
  assert.match(contactCountColumn, /onClick=\{\(\) => openDetail\(r, "contacts"\)\}/);
});
