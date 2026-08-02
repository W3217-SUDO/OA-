import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(
  new URL("./src/SystemCenterPage.tsx", import.meta.url),
  "utf8",
);
const cacheStart = source.indexOf(
  '} else if (initialView === "system-management-cache")',
);
const cacheEnd = source.indexOf(
  '} else if (initialView === "system-management-menu")',
  cacheStart,
);
const cacheBlock = source.slice(cacheStart, cacheEnd);

test("legacy cache pagination shows the total-row footer", () => {
  assert.match(cacheBlock, /showTotal\s*:/);
});
