import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const css = readFileSync(new URL("./src/case-center.css", import.meta.url), "utf8");
const sharedCss = readFileSync(new URL("./src/styles.css", import.meta.url), "utf8");

test("shared data cards keep controls fixed and scroll their table area", () => {
  assert.match(sharedCss, /\.page-workbench:has\(> \.ant-card > \.ant-card-body > \.ant-table-wrapper\)/);
  assert.match(sharedCss, /\.page-workbench > \.ant-card:has\(> \.ant-card-body > \.ant-table-wrapper\)[^{]*\{[^}]*overflow:\s*hidden/);
  assert.match(sharedCss, /\.page-workbench > \.ant-card > \.ant-card-body > \.ant-table-wrapper\s*\{[^}]*overflow:\s*auto/);
  assert.match(sharedCss, /\.ant-table-thead > tr > th\s*\{[^}]*position:\s*sticky/);
});

test("case detail keeps summaries fixed and scrolls the lower record area", () => {
  assert.match(css, /\.page-workbench:has\(\.case-detail-static-root\)\{overflow:hidden\}/);
  assert.match(css, /\.case-detail-static-root \.ant-drawer-body\{[^}]*overflow:hidden/);
  assert.match(css, /\.case-detail-static-root \.case-detail-workbench\{[^}]*flex-direction:column[^}]*overflow:hidden/);
  assert.match(css, /\.case-detail-static-root \.case-detail-body-grid\{[^}]*flex:1 1 auto[^}]*overflow:auto/);
});
