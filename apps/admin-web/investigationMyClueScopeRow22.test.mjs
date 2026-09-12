import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/investigation/InvestigationCenterPage.tsx", import.meta.url), "utf8");

test("personal clue routes request the server-side mine scope", () => {
  assert.match(source, /initialTab\.includes\("-my-"\)[\s\S]{0,260}\? "mine"/);
});

test("admin personal queues retain the same owner-only frontend guard", () => {
  assert.match(source, /initialTab\.includes\("-my-"\)[\s\S]{0,500}String\(row\.owner \|\| ""\)\.toLocaleLowerCase\(\)/);
  const ownerGuard = source.slice(source.indexOf('initialTab.includes("-my-") &&'), source.indexOf('if (initialTab.endsWith("-no-fee"))'));
  assert.doesNotMatch(ownerGuard, /isActualAdmin|profile\.role/);
});
