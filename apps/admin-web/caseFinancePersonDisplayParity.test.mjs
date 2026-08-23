import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const casePage = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");
const financePage = fs.readFileSync(new URL("./src/FinanceCenterPage.tsx", import.meta.url), "utf8");

test("case people preserve explicit and historical names without exposing accounts", () => {
  assert.match(casePage, /const explicitName = String\(displayName \|\| ""\)\.trim\(\);/);
  assert.match(casePage, /if \(!normalized\) return "—";/);
  assert.match(casePage, /return \/\[\\u3400-\\u9fff\]\/.test\(normalized\) \? normalized :/);
  assert.doesNotMatch(casePage, /\?\.label \|\| normalized/);
  assert.match(casePage, /casePersonDisplayName\(row\.uploader,row\.uploader_display_name\)/);
  assert.match(casePage, /archive_submitter_display_name\|\|row\.owner_display_name/);
});

test("finance still resolves person labels from the people option source", () => {
  assert.match(financePage, /api\.get\("\/people\/options"\)/);
  assert.match(financePage, /financePersonNameMap\.get\(key\)/);
});
