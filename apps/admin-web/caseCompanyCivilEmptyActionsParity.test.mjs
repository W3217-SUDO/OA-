import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("company case list actions follow the legacy route rather than result count", () => {
  assert.match(
    source,
    /export const shouldShowCaseListActions = \(initialView: string\) =>\s*isMyCaseListRoute\(initialView\) \|\| isCompanyCaseListRoute\(initialView\);/,
  );
  assert.match(
    source,
    /\{shouldShowCaseListActions\(initialView\)&&<div className=\{`case-bottom-actions/,
  );
});
