import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/InvestigationCenterPage.tsx", import.meta.url), "utf8");

test("personal clue routes request the server-side mine scope", () => {
  assert.match(source, /initialTab\.includes\("-my-"\)[\s\S]{0,260}\? "mine"/);
});

test("admin personal queues retain the same owner-only frontend guard", () => {
  assert.match(source, /initialTab\.includes\("-my-"\)[\s\S]{0,500}String\(row\.owner \|\| ""\)\.toLocaleLowerCase\(\)/);
  assert.doesNotMatch(source, /initialTab\.includes\("-my-"\)[\s\S]{0,100}profile\.role !== "admin"/);
});
