import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/HrCenterPage.tsx", import.meta.url), "utf8");

test("account-only system users remain manageable from employee management", () => {
  assert.match(source, /title:'用户名'/);
  assert.match(source, /openPasswordReset\(r\)/);
  assert.doesNotMatch(source, /if\(row\.id<0\)\{message\.error\('请先补建正式员工档案后再重置密码'\)/);
});
