import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(
  new URL("./src/OrganizationCenterPage.tsx", import.meta.url),
  "utf8",
);

test("department list keeps the legacy 15-row page boundary", () => {
  const departmentTable = source.match(
    /dataSource=\{departments\}[\s\S]*?pagination=\{\{([\s\S]*?)\}\}\s*\/>/,
  );

  assert.ok(departmentTable, "department table configuration should exist");
  assert.match(departmentTable[1], /pageSize:\s*15\b/);
});
