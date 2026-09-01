import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("direct seal submission honors the backend sync-seal handoff contract", () => {
  assert.match(source, /const submitApplication = forcedSubmit \?\? Boolean\(submitFromForm\);/);
  assert.match(source, /submit: Boolean\(submitApplication\)/);
});
