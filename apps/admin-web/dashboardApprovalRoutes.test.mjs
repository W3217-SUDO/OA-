import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";


const appSource = readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");


test("dashboard approval shortcuts open the exact pending workspaces", () => {
  assert.match(appSource, /待审批合同:\s*"contract-audit-pending"/u);
  assert.match(appSource, /待审批用印:\s*"seal-audit-pending"/u);
});
