import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/AuditLogPage.tsx", import.meta.url), "utf8");

test("audit log exposes query reset, module filter, pagination and detail navigation", () => {
  assert.match(source, /setKeyword\(""\); setModule\(""\); setPage\(1\); void load\(1\)/);
  assert.match(source, /allowClear/);
  assert.match(source, /pagination=\{\{ current: page, total/);
  assert.match(source, /onChange: \(p\) => \{ setPage\(p\); void load\(p\); \}/);
  assert.match(source, /openBusiness\(row\)/);
});
