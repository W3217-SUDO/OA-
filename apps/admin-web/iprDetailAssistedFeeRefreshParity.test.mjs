import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /const refreshAssistedFees = \(\) => \{[\s\S]*?if \(detail\) void loadAssistedFees\(detail\.id, assistedFeesPageState\.page, assistedFeesPageState\.pageSize\);[\s\S]*?\};/,
  "IPR detail assisted-fee refresh should reload the current server page.",
);

assert.match(
  center,
  /title="资助明细"[\s\S]*?onClick=\{refreshAssistedFees\}>刷新<\/Button>/,
  "IPR detail assisted-fee section should expose the legacy refresh action.",
);

console.log("ipr detail assisted-fee refresh parity: PASS");
