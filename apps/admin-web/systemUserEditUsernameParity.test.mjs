import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const pageSource = fs.readFileSync(path.join(here, "src", "SystemCenterPage.tsx"), "utf8");

const between = (start, end) => {
  const startIndex = pageSource.indexOf(start);
  const endIndex = pageSource.indexOf(end, startIndex);
  assert.ok(startIndex >= 0 && endIndex > startIndex, `missing source range: ${start} -> ${end}`);
  return pageSource.slice(startIndex, endIndex);
};

test("system user editor keeps the legacy editable username when updating an account", () => {
  const editHelper = between("const editUser = (row?: SystemUser)", "const saveUser = async");
  const editor = between('<Modal\n          open={userOpen}', '<Modal\n          open={Boolean(resettingUser)}');

  assert.match(editHelper, /row\s*\?\s*\{\s*\.\.\.row,/s, "edit mode should prefill the existing account username");
  assert.match(editor, /<Form\.Item\s+label="登录账号"\s+name="username"[\s\S]*?rules=\{\[\{ required: true \}, \{ min: 3 \}\]\}/, "the editor should expose the existing username field");
  assert.doesNotMatch(editor, /\{!editingUser && \(/, "username must not disappear while editing an existing account");
  assert.match(pageSource, /api\.patch\(`\/system\/users\/\$\{editingUser\.id\}`, payload\)/, "the existing update request should submit the edited username");
});
