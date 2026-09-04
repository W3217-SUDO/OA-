import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /key:"platform-fees",label:"平台费用"/);
assert.match(source, /传统模式：新增平台代理费/);
assert.match(source, /openCaseFeeBySubtype\("平台",PLATFORM_AGENCY_FEE_SUBTYPE\)/);
assert.match(source, /expenseScope === "平台" && agencyPreset \? PLATFORM_AGENCY_FEE_SUBTYPE/);
assert.match(source, /title=\{activeFeeContractScope === "平台" && feeSubtypePreset === "agency" \? "新增平台代理费" : "新增费用"\}/);

console.log("legacy TradFee platform entry parity contract passed");
