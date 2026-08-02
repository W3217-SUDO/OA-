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
const cacheHandlers = source.slice(
  source.indexOf("const clearCache = async"),
  source.indexOf("const editMenu =", source.indexOf("const clearCache = async")),
);
const apiSource = fs.readFileSync(
  new URL("../api-server/app/main.py", import.meta.url),
  "utf8",
);

test("legacy cache pagination shows the total-row footer", () => {
  assert.match(cacheBlock, /showTotal\s*:/);
});

test("legacy cache pagination exposes all page-size options", () => {
  assert.match(
    cacheBlock,
    /pageSizeOptions:\s*\["10",\s*"15",\s*"20",\s*"50",\s*"100",\s*"200"\]/,
  );
});

test("legacy cache pagination exposes a GO quick-jump control", () => {
  assert.match(cacheBlock, /showQuickJumper\s*:/);
  assert.match(cacheBlock, /cacheJumpPage/);
});

test("cache page-size changes reload the requested page and size", () => {
  assert.match(cacheBlock, /onChange:\s*\(page, pageSize\).*loadCaches\(page, pageSize\)/s);
});

test("cache clear actions keep confirmation and both feedback paths", () => {
  assert.match(cacheBlock, /Popconfirm/);
  assert.match(cacheHandlers, /message\.success/);
  assert.match(cacheHandlers, /message\.error/);
});

test("cache list and clear endpoints require an administrator", () => {
  const cacheApi = apiSource.slice(
    apiSource.indexOf('@app.get(f"{settings.api_prefix}/system/caches")'),
    apiSource.indexOf("def _law_firm_contact_dict", apiSource.indexOf('@app.get(f"{settings.api_prefix}/system/caches")')),
  );
  assert.equal((cacheApi.match(/_require_admin\(identity\)/g) || []).length, 3);
});
