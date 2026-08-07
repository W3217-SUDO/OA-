import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("court-information step returns to litigants without saving", () => {
  assert.match(source, /createStep === 2/);
  assert.match(source, /setCreateStep\(1\)/);
  assert.match(source, />上一步<\/Button>/);
});
