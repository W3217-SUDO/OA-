import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case reminders use the case endpoints and detail permissions", () => {
  assert.match(source, /api\.post\(`\/cases\/\$\{viewingCounselCase\.id\}\/reminders`/);
  assert.match(source, /api\.delete\(`\/cases\/\$\{viewingCounselCase\.id\}\/reminders\/\$\{reminder\.id\}`/);
  assert.match(source, /can_create_reminder/);
  assert.match(source, /can_delete_reminder/);
});

test("the detail side panel exposes reminder and both log creators", () => {
  const panel = source.slice(source.indexOf('className="case-detail-side-panel"'), source.indexOf('</aside>', source.indexOf('className="case-detail-side-panel"')));
  assert.match(panel, /case-detail-side-title/);
  assert.match(panel, /openCounselLogCreator\("case"\)/);
  assert.match(panel, /openCounselLogCreator\("refund"\)/);
  assert.match(panel, /setReminderOpen\(true\)/);
});

test("logs retain their selected case when opened from a list or detail", () => {
  assert.match(source, /setCaseLogTarget\(row\)/);
  assert.match(source, /const targetCase = caseLogTarget \|\| viewingCounselCase;/);
  assert.match(source, /api\.post\(`\/cases\/\$\{targetCase\.id\}\/logs`,\{content:logContent\}\)/);
  assert.match(source, /setCaseLogTarget\(null\)/);
});
