import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");
const listRequest = source.match(/api\.get\("\/ipr\/cases",\s*\{[\s\S]*?params:\s*\{[\s\S]*?\n\s*\}\s*,?\n\s*\}\s*\)/)?.[0] || "";

test("IPR main list uses server-side pagination with the legacy 15-row default", () => {
  assert.match(
    source,
    /\[page,\s*setPage\]\s*=\s*useState\(1\)/,
    "IPR list should keep a current page state instead of always loading the first page",
  );
  assert.match(
    source,
    /\[pageSize,\s*setPageSize\]\s*=\s*useState\(15\)/,
    "IPR list should default to the legacy 15-row page size",
  );
  assert.match(
    source,
    /api\.get\(\"\/ipr\/cases\"[\s\S]*page[\s\S]*page_size/s,
    "IPR list request should send both page and page_size to the backend",
  );
  assert.doesNotMatch(
    listRequest,
    /page_size:\s*100/,
    "IPR list should not work around missing pagination by loading 100 rows at once",
  );
  assert.match(
    source,
    /setTotal\(data\.total\)/,
    "IPR list should keep using the backend total",
  );
  assert.match(
    source,
    /setPage\(data\.page\s*\?\?\s*[^)]+\)/,
    "IPR list should accept the backend-returned page number",
  );
  assert.match(
    source,
    /setPageSize\(data\.page_size\s*\?\?\s*[^)]+\)/,
    "IPR list should accept the backend-returned page size",
  );
  assert.match(
    source,
    /setPages\(data\.pages\s*\?\?\s*[^)]+\)/,
    "IPR list should accept the backend-returned page count",
  );
  assert.match(
    source,
    /pagination=\{\{[\s\S]*current:\s*page[\s\S]*pageSize:\s*pageSize[\s\S]*onChange:/s,
    "IPR table pagination should be controlled and reload through the server",
  );
});
