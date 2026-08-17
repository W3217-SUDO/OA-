import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("approved contract forwards the user's direct seal submission intent", () => {
  assert.match(source, /submit: Boolean\(enterSealCenter\)/);
  assert.doesNotMatch(source, /submit: wizardDraft\.status === "审批中" && Boolean\(enterSealCenter\)/);
});
