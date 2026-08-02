import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/caseLegacyParity.ts", import.meta.url), "utf8");

test("legacy case list defaults keep the old list, schedule, phase and execution matrix", () => {
  assert.match(source, /export const getLegacyCaseListDefaults/);
  assert.match(source, /list: \{ pageSize: 10/);
  assert.match(source, /schedule: \{ pageSize: 15/);
  assert.match(source, /phase: \{ pageSize: 15/);
  assert.match(source, /execution: \{ pageSize: 10/);
  assert.match(source, /sortField: "T\.LawfulDay"/);
});

test("legacy case list exposes the selected-row operations as a stable contract", () => {
  assert.match(source, /export const getLegacyCaseListOperationLabels/);
  for (const key of ["query", "reset", "exportSelected", "exportAll", "exportManifest", "participant", "phase", "court", "delete"]) {
    assert.match(source, new RegExp(`${key}:`));
  }
});

test("legacy case list permission matrix blocks unsafe operations and preserves read-only access", () => {
  assert.match(source, /export const getLegacyCaseListOperationState/);
  assert.match(source, /selectedCount === 0/);
  assert.match(source, /status === "待归档审核"/);
  assert.match(source, /status === "已归档"/);
  assert.match(source, /role !== ""/);
  assert.match(source, /canDelete: false/);
});

test("legacy case list mode maps exact routes without leaking special-case defaults", () => {
  assert.match(source, /export const getLegacyCaseListMode/);
  for (const route of ["case-company-civil", "case-company-criminal", "case-company-arbitration", "case-company-schedule", "case-company-execution"]) {
    assert.match(source, new RegExp(route.replaceAll("-", "\\-")));
  }
  assert.match(source, /return "schedule"/);
  assert.match(source, /return "execution"/);
});
