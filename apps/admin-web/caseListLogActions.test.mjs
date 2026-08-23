import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case lists reuse the detail log view and existing case log API", () => {
  assert.match(source, /const openCaseLogViewer = \(row: CaseRow\) => \{\s*void openCounselDetail\(row, "case-logs"\);/);
  assert.match(source, /api\.post\(`\/cases\/\$\{targetCase\.id\}\/logs`,\{content:logContent\}\)/);
});

test("new list log button reads only action capabilities", () => {
  assert.match(source, /const openCaseListLogCreator = \(row: CaseRow\) => \{\s*if \(!getCaseCapability\(row\)\.can_create_log\)/);
  assert.doesNotMatch(source, /openCaseListLogCreator[\s\S]{0,300}profile\.role/);
});

test("historical Chinese names remain visible when their account is unavailable", () => {
  assert.match(source, /const matchedName = option\?\.label\.replace/);
  assert.match(source, /if \(matchedName\) return matchedName;/);
  assert.match(source, /return \/\[\\u3400-\\u9fff\]\/.test\(normalized\) \? normalized :/);
});
