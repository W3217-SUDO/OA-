import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /const resetMainListSearch = \(\) => \{[\s\S]*?setKeyword\(""\);[\s\S]*?setAnnualFeeMonitoringFilter\(""\);[\s\S]*?setPage\(1\);[\s\S]*?\};/,
  "IPR main-list reset should clear keyword and annual-fee filters and return pagination to page one.",
);

assert.match(
  center,
  /<Button onClick=\{\(\) => void load\(1, pageSize\)\}>查询<\/Button>[\s\S]*?<Button onClick=\{resetMainListSearch\}>重置<\/Button>/,
  "IPR main-list toolbar should expose a dedicated reset action beside search.",
);

console.log("ipr main-list search reset parity: PASS");
