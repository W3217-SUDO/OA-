import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const page = await readFile(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("department contracts retain the backend customer-manager scope", () => {
  assert.match(
    page,
    /api\.get\("\/records", \{ params: \{ \.\.\.recordsParams, scope: listViewConfig\.scope, page: 1, page_size: 100 \} \}\)/,
  );
  assert.doesNotMatch(
    page,
    /initialView === "contract-dept"\s*\?\s*allRows\.filter\(\(x\) => x\.department === profile\.department\)/,
  );
});
