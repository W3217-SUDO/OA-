import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("customer create related documents retain separate legacy preview and download actions", () => {
  const createViewStart = source.indexOf('initialView === "customer-new"');
  const createDocumentsStart = source.indexOf('key:"documents"', createViewStart);
  const drawerStart = source.indexOf('title={`客户详情：${contacts?.title || ""}`}');
  assert.ok(createViewStart >= 0 && createDocumentsStart > createViewStart && drawerStart > createDocumentsStart);

  const createDocuments = source.slice(createDocumentsStart, drawerStart);
  assert.match(createDocuments, /onClick=\{\(\)=>void viewDocument\(row\)\}/);
  assert.match(createDocuments, /onClick=\{\(\)=>void downloadDocument\(row\)\}/);
});
