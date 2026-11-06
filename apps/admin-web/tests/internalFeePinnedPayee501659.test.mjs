import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const select = readFileSync(new URL("../src/components/KeywordPersonSelect.tsx", import.meta.url), "utf8");
const page = readFileSync(new URL("../src/legal/CaseCenterPage.tsx", import.meta.url), "utf8");

test("501659 KeywordPersonSelect shows pinned options before typing and first while searching", () => {
  assert.match(select, /pinnedValues = \[\]/);
  assert.match(select, /options=\{searching \? options : pinned\}/);
  assert.match(select, /\[\.\.\.pinned, \.\.\.allOptions\.filter/);
});

test("501659 internal fee payee pins 外部合作律师 only for 调档费", () => {
  assert.match(page, /externalCounselPayeeValues = useMemo\(\(\) => feeEmployeeOptions\.filter\(\(item\) => String\(item\.label \|\| ""\)\.split\("（"\)\[0\]\.trim\(\) === "外部合作律师"\)/);
  assert.match(page, /pinnedValues=\{feeForm\.getFieldValue\(\["items", field\.name, "expense_subtype"\]\) === "调档费" \? externalCounselPayeeValues : undefined\}/);
  assert.equal((page.match(/pinnedValues=/g) || []).length, 1);
});
