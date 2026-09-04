import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");
const policy = fs.readFileSync(new URL("./src/contractWorkflowPolicy.mjs", import.meta.url), "utf8");
const shell = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("contract archive list uses a dedicated paged API, filters, export, and detail action", () => {
  assert.match(page, /api\.get\("\/contracts\/archive-list", \{ params: archiveParams \}\)/);
  assert.match(page, /\/contracts\/archive-list\/export-excel/);
  assert.match(page, /name="archive_status"/);
  assert.match(page, /name="archive_date"/);
  assert.match(page, /archiveColumns/);
  assert.match(page, /onClick=\{\(\) => void openViewing\(row\)\}/);
  assert.match(page, /onClick=\{\(\) => void openRelatedCustomer\(row\)\}/);
  assert.match(policy, /"contract-archive"/);
  assert.match(shell, /key: "contract-archive", label: "合同归档"/);
});
