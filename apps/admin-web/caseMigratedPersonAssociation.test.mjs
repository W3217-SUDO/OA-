import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case source-person cells fall back to the migrated business owner", () => {
  const fallback = "row.data.source_person||row.data.business_owner||row.owner";
  assert.equal(source.split(fallback).length - 1, 2);
  assert.match(source, /row\.data\.source_person_display_name\|\|row\.data\.business_owner_display_name\|\|row\.owner_display_name/);
  assert.match(source, /!\["姓名待维护", "【待补充中文姓名】"\]\.includes\(explicitName\)/);
});
