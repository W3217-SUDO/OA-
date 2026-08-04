import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("customer document view preserves legacy browser preview before download fallback", () => {
  assert.match(source, /const viewDocument = async \(file: Attachment\) =>/);
  assert.ok(source.includes("const previewable = /\\.(pdf|jpe?g|png|gif|webp|tiff?)$/i.test(file.original_name);"));
  assert.match(source, /setCustomerDocumentPreview\(\{ name: file\.original_name, url \}\)/);
  assert.match(source, /onClick=\{\(\)=>void viewDocument\(row\)\}/);
  assert.match(source, /<Modal open=\{Boolean\(customerDocumentPreview\)\}/);
});
