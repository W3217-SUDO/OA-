import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  GLOBAL_CASE_SEARCH_CONTEXT_KEY,
  GLOBAL_CASE_SEARCH_ROUTE,
  buildGlobalCaseSearchContext,
  readStoredGlobalCaseSearchContext,
} from "./globalCaseSearchParity.mjs";

test("global case search opens my cases with a partial keyword", () => {
  assert.equal(GLOBAL_CASE_SEARCH_CONTEXT_KEY, "sunhold:case-list-return");
  assert.equal(GLOBAL_CASE_SEARCH_ROUTE, "case-mine");
  assert.deepEqual(buildGlobalCaseSearchContext("  2600431  "), {
    route: "case-mine",
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
  const source = await readFile(new URL("./GlobalSearch.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(source, /<Drawer\b/);
  assert.doesNotMatch(source, /全局检索/);
  assert.match(source, /<Input\.Search[\s\S]*onSearch=\{search\}/);
});
