import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(
  new URL("./src/OrganizationCenterPage.tsx", import.meta.url),
  "utf8",
);

test("role list keeps the legacy 15-row page boundary", () => {
  const roleTable = source.match(
    /dataSource=\{roles\}[\s\S]*?pagination=\{\{([\s\S]*?)\}\}\s*\/>/,
  );

  assert.ok(roleTable, "role table configuration should exist");
  assert.match(roleTable[1], /pageSize:\s*15\b/);
});
