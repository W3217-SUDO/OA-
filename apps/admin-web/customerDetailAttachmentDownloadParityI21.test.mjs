import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

test("customer detail documents retain separate legacy preview and download actions", () => {
  const detailTabsStart = source.indexOf('className="customer-view-tabs"');
  const detailActionsStart = source.indexOf('className="customer-detail-actions"', detailTabsStart);
  assert.ok(detailTabsStart >= 0 && detailActionsStart > detailTabsStart);

  const detailTabs = source.slice(detailTabsStart, detailActionsStart);
  assert.match(detailTabs, /key: "documents"/);
  assert.match(detailTabs, /onClick=\{\(\)=>void viewDocument\(row\)\}/);
  assert.match(detailTabs, /onClick=\{\(\)=>void downloadDocument\(row\)\}/);
});
