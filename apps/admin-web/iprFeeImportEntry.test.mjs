import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");
const app = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
assert.match(center, /案件票据导入/);
assert.match(center, /案件发票导入/);
assert.match(center, /case-files-receipt/);
assert.match(center, /case-files-invoice/);
assert.match(app, /route\.startsWith\(\"case-\"\)/);
assert.match(app, /IprCenterPage initialView=\{active\} onNavigate=\{navigate\}/);
console.log("ipr fee import entry: PASS");
