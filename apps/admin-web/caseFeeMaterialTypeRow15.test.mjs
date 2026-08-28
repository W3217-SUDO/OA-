import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const drawerStart = source.indexOf('<Drawer\n        open={Boolean(feeCase)}');
const drawerEnd = source.indexOf("</Drawer>", drawerStart);
const drawer = source.slice(drawerStart, drawerEnd);

test("row 15 removes material type from the case fee create drawer", () => {
  assert.ok(drawerStart >= 0 && drawerEnd > drawerStart);
  assert.doesNotMatch(drawer, /label="关联材料类型"/);
  assert.doesNotMatch(drawer, /name="source_file_type"/);
});

test("row 15 keeps the required fee fields", () => {
  assert.match(drawer, /name=\{\[field\.name, "contract_record_id"\]\}/);
  assert.match(drawer, /name=\{\[field\.name, "expense_subtype"\]\}/);
  assert.match(drawer, /name=\{\[field\.name, "amount"\]\}/);
});
