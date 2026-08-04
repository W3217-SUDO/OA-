import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /type IprReminder = \{[\s\S]*?creator: string;[\s\S]*?\};/,
  "IPR reminder records should retain the creator needed for the legacy delete permission gate.",
);

assert.match(
  center,
  /const canDeleteIprReminder = \(row: IprReminder\) => row\.creator === profile\.username \|\| \["admin", "manager"\]\.includes\(profile\.role \|\| ""\);/,
  "IPR reminder deletion should be limited to its creator or a manager role before rendering the action.",
);

assert.match(
  center,
  /detail\.status === "在办" && canDeleteIprReminder\(row\) \? \([\s\S]*?confirmIprDeletion\("reminder", row\.content, \(\) => deleteReminder\(row\)\)/,
  "The reminder delete control should combine the active-case gate with the legacy creator or manager gate.",
);

console.log("ipr reminder delete permission parity: PASS");
