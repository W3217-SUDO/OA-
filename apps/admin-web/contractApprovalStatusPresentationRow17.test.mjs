import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { displayContractStatus } from "./src/contractStatusPresentation.mjs";

const pageSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("approved contract status is canonically presented as 审批通过", () => {
  assert.equal(displayContractStatus("审批通过"), "审批通过");
  assert.equal(displayContractStatus("已通过"), "审批通过");
  assert.equal(displayContractStatus("履行中"), "审批通过");
  assert.equal(displayContractStatus("审批中"), "审批中");
  assert.equal(displayContractStatus("已拒绝"), "已拒绝");
  assert.equal(displayContractStatus(null), null);
});

test("contract lists, detail, approval steps, and both wizard status entries use the presentation mapping", () => {
  assert.match(pageSource, /render: textCell/);
  assert.match(pageSource, /children:displayContractStatus\(viewing\.status\)/);
  assert.equal((pageSource.match(/displayContractStatus\(wizardDraft\.status\)/g) || []).length, 4);
  assert.match(pageSource, /displayContractStatus\(s\.status\)/);
});

test("status presentation keeps workflow comparisons on canonical raw values", () => {
  assert.match(pageSource, /wizardDraft\?\.status === "审批中"/);
  assert.match(pageSource, /step\.status === "待审批"/);
  assert.match(pageSource, /colors\[wizardDraft\.status\]/);
  assert.doesNotMatch(pageSource, /wizardDraft\.status\s*=\s*displayContractStatus/);
});
