import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/UserCenterPage.tsx", import.meta.url), "utf8");

test("user center keeps legacy account menu tabs", () => {
  assert.ok(source.includes("基本资料"));
  assert.ok(source.includes("密码修改"));
  assert.ok(source.includes("个性配置"));
});

test("user center password form rejects a new password equal to the current password", () => {
  assert.match(source, /name="new_password"[\s\S]*新密码不能与原密码相同/);
  assert.match(
    source,
    /getFieldValue\('current_password'\)[\s\S]*value!==getFieldValue\('current_password'\)/,
  );
});