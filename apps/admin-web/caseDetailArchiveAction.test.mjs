import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("case detail exposes guarded archive request action", () => {
  assert.match(source, /counselDetailCapabilities\.can_archive/);
  assert.match(source, /申请归档/);
  assert.match(source, /disabled=\{\["待归档审核","已归档"\]\.includes\(viewingCounselCase\.status\)\}/);
  assert.match(source, /openArchive\(viewingCounselCase\)/);
});
