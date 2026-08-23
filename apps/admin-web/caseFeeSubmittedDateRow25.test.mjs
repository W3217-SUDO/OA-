import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const feeSection = source.slice(source.indexOf('{key:"firm-fees"'), source.indexOf('{key:"reminders"'));

const dateColumns = [...feeSection.matchAll(/data\.submitted_at\|\|row\.created_at\|\|row\.data\.created_at/g)];
assert.equal(dateColumns.length, 2, "law-firm and internal-fee tables retain submitted-date fallbacks");
assert.match(source, /originalArchiveColumns:any\[\]=\[[\s\S]*?openCounselDetail\(row\)/);
assert.doesNotMatch(source, /originalArchiveColumns:any\[\]=\[[\s\S]{0,1800}openCaseTasks\(row\)/);

console.log("case fee submitted date row 25: PASS");
