import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const page = fs.readFileSync(path.join(root, "src", "CaseCenterPage.tsx"), "utf8");

test("case detail keeps reminder and both log creators in the side panel", () => {
  const panel = page.slice(page.indexOf('className="case-detail-side-panel"'), page.indexOf('</aside>', page.indexOf('className="case-detail-side-panel"')));
  assert.match(panel, /case-detail-side-title/);
  assert.match(panel, /setReminderOpen\(true\)/);
  assert.match(panel, /openCounselLogCreator\("case"\)/);
  assert.match(panel, /openCounselLogCreator\("refund"\)/);
});

test("reminder and log creators use persistent case endpoints", () => {
  assert.match(page, /\/cases\/\$\{viewingCounselCase\.id\}\/reminders/);
  assert.match(page, /\/cases\/\$\{targetCase\.id\}\/logs/);
  assert.match(page, /setCaseLogTarget\(viewingCounselCase\)/);
  assert.match(page, /setCaseLogTarget\(null\)/);
});
