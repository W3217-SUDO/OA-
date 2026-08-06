import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("company contract view keeps the legacy whole-contract delete action", () => {
  assert.match(source, /const deleteCompanyContract = \(contract: Contract\)/);
  assert.match(source, /api\.post\("\/contracts\/company\/delete", \{ contract_ids: \[contract\.id\] \}\)/);
  assert.match(source, /initialView === "contract-company"/);
  assert.match(source, /<Button danger disabled=\{!selected\} onClick=\{\(\)=>needSelected\(\(\)=>deleteCompanyContract\(selected!\)\)\}\>删除合同<\/Button>/);
});
