import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract seal form requires a configured approver and displays directory names", () => {
  assert.equal((source.match(/name="approver"/g) || []).length, 2);
  assert.match(source, /options=\{approvalOptions\}/);
  assert.match(source, /message: "请选择用印审批人"/);
});

test("contract seal submission sends the selected approver to the API", () => {
  assert.match(source, /api\.post\(`\/contracts\/\$\{wizardDraft\.id\}\/seal-application`/);
  assert.match(source, /\.\.\.sealValues/);
});
