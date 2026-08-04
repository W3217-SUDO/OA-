import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const pageSource = fs.readFileSync(path.join(here, "src", "SystemCenterPage.tsx"), "utf8");

test("system user list exposes a refresh action that keeps the current query", () => {
  const start = pageSource.indexOf('} else if (initialView === "system-users")');
  const end = pageSource.indexOf('<Table', start);
  assert.ok(start >= 0 && end > start, "system user toolbar should be present");
  const toolbar = pageSource.slice(start, end);

  assert.match(toolbar, /aria-label="刷新系统用户"/, "system user toolbar should expose an accessible refresh action");
  assert.match(toolbar, /icon=\{<ReloadOutlined \/>\}/, "refresh should use the standard reload icon");
  assert.match(toolbar, /onClick=\{\(\) => void loadUsers\(keyword\)\}/, "refresh should reload the current query instead of clearing it");
});
