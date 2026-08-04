import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(path.join(here, "src", "OrganizationCenterPage.tsx"), "utf8");

test("department list keeps the legacy explicit GO pagination action", () => {
  const start = source.indexOf('dataSource={departments}');
  const end = source.indexOf('          />', start);
  assert.ok(start >= 0 && end > start, "department table should be present");
  const departmentTable = source.slice(start, end);
  const roleStart = source.indexOf('dataSource={roles}');
  const roleEnd = source.indexOf('          />', roleStart);
  assert.ok(roleStart >= 0 && roleEnd > roleStart, "role table should remain present");
  const roleTable = source.slice(roleStart, roleEnd);

  assert.match(departmentTable, /pageSize: 15/, "department list should keep the legacy 15-row page boundary");
  assert.match(departmentTable, /showQuickJumper: \{ goButton: "GO" \}/, "department list should retain the legacy cPaging GO button instead of Enter-only page jump");
  assert.match(roleTable, /showQuickJumper: true/, "this department-only repair must not alter role pagination");
});
