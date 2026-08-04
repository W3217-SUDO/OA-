import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /const refreshIprFiles = \(\) => \{[\s\S]*?if \(detail\) void loadIprFiles\(detail\.id, filesPageState\.page, filesPageState\.pageSize\);[\s\S]*?\};/,
  "IPR detail attachment refresh should reload the current server page without changing its pagination state.",
);

assert.match(
  center,
  /title="案件文书与附件"[\s\S]*?extra=\{<Button size="small" onClick=\{refreshIprFiles\}>刷新<\/Button>\}/,
  "IPR detail attachment section should expose the legacy refresh action.",
);

console.log("ipr detail attachment refresh parity: PASS");
