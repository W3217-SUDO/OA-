import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case detail exposes a real back-to-list action", () => {
  assert.match(source, /data-testid=\"case-detail-back\"/);
  assert.match(source, /返回案件列表/);
  assert.match(source, /isCaseDetailView \? onNavigate\?\.\("case-mine"\)/);
  assert.doesNotMatch(source, /isCaseDetailView \? onNavigate\?\.\("case-mine-civil"\)/);
});
