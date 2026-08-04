import assert from "node:assert/strict";
import fs from "node:fs";

const page = fs.readFileSync(new URL("./src/IprOfficialFilePage.tsx", import.meta.url), "utf8");

assert.match(
  page,
  /const\s+resetSearch\s*=\s*\(\)\s*=>\s*\{[\s\S]*?setKeyword\(""\);[\s\S]*?setStatus\(""\);[\s\S]*?setPage\(1\);[\s\S]*?load\(1\s*,\s*pageSize\)/,
  "official-file search reset should clear filters and reload the first page",
);
assert.match(
  page,
  /onClick=\{\(\)\s*=>\s*resetSearch\(\)\}[\s\S]*?重置/,
  "official-file search controls should expose the legacy reset entry",
);

console.log("ipr official-file search reset parity: PASS");
