import assert from "node:assert/strict";
import fs from "node:fs";

const page = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  page,
  /const\s+openIprCaseTask\s*=\s*\(\s*record:\s*IprRecord\s*\)\s*=>\s*\{[\s\S]*?sessionStorage\.setItem\([\s\S]*?sunhold:task-create-context[\s\S]*?onNavigate\?\.\("task-my-created"\)/,
  "IPR detail should open the task center with a prefilled case-task draft",
);
assert.match(
  page,
  /case_no:\s*record\.serial_no/,
  "IPR task context should prefill the case number",
);
assert.match(
  page,
  /customer:\s*record\.customer/,
  "IPR task context should prefill the customer",
);
assert.match(
  page,
  /onClick=\{\(\s*\)\s*=>\s*openIprCaseTask\(\s*detail\s*\)\s*\}[^>]*>\s*\u6848\u4ef6\u4efb\u52a1/,
  "IPR detail actions should expose the legacy case-task entry",
);

console.log("ipr case task entry parity: PASS");
