import assert from "node:assert/strict";
import fs from "node:fs";
const source=fs.readFileSync(new URL("./src/InvestigationCenterPage.tsx",import.meta.url),"utf8");
assert.match(source,/contract\.status !== "草稿"/);
assert.match(source,/label="调查员"[\s\S]*name="owner"/);
console.log("9.1 row 15 subtask contract gate passed");
