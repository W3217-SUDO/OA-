import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(path.join(here, "src", "HrCenterPage.tsx"), "utf8");

test("employee list refresh keeps current filters and clears stale action state", () => {
  const start = source.indexOf("const listPanel=");
  const end = source.indexOf("<Table className=\"employee-list-table\"", start);
  assert.ok(start >= 0 && end > start, "employee list toolbar should be present");
  const toolbar = source.slice(start, end);

  assert.match(toolbar, /aria-label="刷新员工列表"/, "employee list should expose an accessible refresh action");
  assert.match(toolbar, /icon=\{<ReloadOutlined\/>\}/, "refresh should use the standard reload icon");
  assert.match(toolbar, /onClick=\{\(\)=>changeEmployeePage\(employeePage\)\}/, "refresh should retain filters and page through the existing stale-state-safe helper");
});
