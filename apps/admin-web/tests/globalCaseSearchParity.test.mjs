import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

import {
  GLOBAL_CASE_SEARCH_CONTEXT_KEY,
  GLOBAL_CASE_SEARCH_ROUTE,
  buildGlobalCaseSearchContext,
  readStoredGlobalCaseSearchContext,
} from "../src/globalCaseSearchParity.mjs";

const compiled = await build({
  entryPoints: [fileURLToPath(new URL("../src/workspacePermissions.ts", import.meta.url))],
  bundle: true, write: false, platform: "node", format: "esm", logLevel: "silent",
});
const { isWorkspaceRouteGranted, resolveGrantedMenuRoute } = await import(`data:text/javascript;base64,${Buffer.from(compiled.outputFiles[0].text).toString("base64")}`);

test("global case search opens the dedicated all-type search with a partial keyword", () => {
  assert.equal(GLOBAL_CASE_SEARCH_CONTEXT_KEY, "sunhold:case-list-return");
  assert.equal(GLOBAL_CASE_SEARCH_ROUTE, "case-global-search");
  assert.deepEqual(buildGlobalCaseSearchContext("  2600431  "), {
    route: "case-global-search",
    page: 1,
    pageSize: 15,
    query: { keyword: "2600431" },
  });
});

test("blank global case search does not navigate", () => {
  assert.equal(buildGlobalCaseSearchContext("   "), null);
});

test("stored search context can be read repeatedly before the list accepts it", () => {
  const context = buildGlobalCaseSearchContext("2600431");
  const storage = { getItem: () => JSON.stringify(context) };
  assert.deepEqual(readStoredGlobalCaseSearchContext(storage), context);
  assert.deepEqual(readStoredGlobalCaseSearchContext(storage), context);
});

test("global search no longer ships the legacy right-side result drawer", async () => {
  const source = await readFile(new URL("../src/GlobalSearch.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(source, /<Drawer\b/);
  assert.doesNotMatch(source, /全局检索/);
  assert.match(source, /<Input\.Search[\s\S]*onSearch=\{search\}/);
});

test("dedicated case search preserves its label and case branch while requiring case read authorization", async () => {
  const source = await readFile(new URL("../src/App.tsx", import.meta.url), "utf8");
  assert.match(source, /"case-global-search": "案件搜索"/);
  assert.match(source, /route\.startsWith\("case-"\)\s*\?\s*\(\s*<CaseCenterPage initialView=\{active\}/);
  for (const key of ["case-mine-civil", "case-dept-civil", "case-company-civil", "case-archive-pending"]) {
    const granted = new Set([key]);
    assert.equal(isWorkspaceRouteGranted(GLOBAL_CASE_SEARCH_ROUTE, granted), true);
    assert.equal(resolveGrantedMenuRoute(GLOBAL_CASE_SEARCH_ROUTE, [], granted), GLOBAL_CASE_SEARCH_ROUTE);
  }
  for (const granted of [new Set(), new Set(["task-my-accepted"]), new Set(["contract-my"]), new Set(["case-new-civil"])]) {
    assert.equal(isWorkspaceRouteGranted(GLOBAL_CASE_SEARCH_ROUTE, granted), false);
    assert.equal(resolveGrantedMenuRoute(GLOBAL_CASE_SEARCH_ROUTE, [], granted), "dashboard");
  }
});

test("dynamic contract change routes require authorization to a contract page", () => {
  const route = "contract-change-17-1234567890";
  for (const key of ["contract-mine", "contract-audit"]) {
    const granted = new Set([key]);
    assert.equal(isWorkspaceRouteGranted(route, granted), true);
    assert.equal(resolveGrantedMenuRoute(route, [], granted), route);
  }
  for (const granted of [new Set(), new Set(["task-my-accepted"]), new Set(["case-mine-civil"])]) {
    assert.equal(isWorkspaceRouteGranted(route, granted), false);
    assert.equal(resolveGrantedMenuRoute(route, [], granted), "dashboard");
  }
});
