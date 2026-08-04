import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("customer detail drawer documents retain legacy preview and download actions", () => {
  const drawerStart = source.lastIndexOf("<Drawer");
  const documentsStart = source.indexOf('key: "documents"', drawerStart);
  assert.ok(drawerStart >= 0 && documentsStart > drawerStart);

  const documentsSection = source.slice(documentsStart, documentsStart + 2600);
  assert.match(documentsSection, /onClick=\{\(\) => downloadDocument\(row\)\}/);
  assert.match(documentsSection, /onClick=\{\(\) => void viewDocument\(row\)\}/);
});
