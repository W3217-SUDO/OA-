import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/InvestigationCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /role_ids\?: string\[\]/);
assert.match(source, /\[profile\.role, \.\.\.\(profile\.role_ids \|\| \[\]\)\]\.includes\("admin"\)/);
assert.match(source, /label !== "删除" \|\| initialTab !== "investigation-task-unassigned" \|\| isAdminAccount/);

console.log("9.1 row 16 investigation admin delete visibility passed");
