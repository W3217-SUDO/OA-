import assert from "node:assert/strict";
import fs from "node:fs";

const financeSource = fs.readFileSync(
  new URL("./src/FinanceCenterPage.tsx", import.meta.url),
  "utf8",
);
const platformSource = fs.readFileSync(
  new URL("./src/PlatformFinancePage.tsx", import.meta.url),
  "utf8",
);

assert.match(financeSource, /row\.customer_manager \|\| data\.customer_manager/);
assert.match(financeSource, /row\.customer_manager_display_name \|\| data\.customer_manager_display_name/);
assert.match(platformSource, /item\.customer_manager_display_name \|\|/);
assert.match(platformSource, /item\.claimant_display_name \|\|/);

console.log("incoming customer manager row 14 contract passed");
