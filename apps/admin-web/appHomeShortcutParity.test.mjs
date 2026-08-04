import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("top toolbar restores the legacy dashboard shortcut", () => {
  assert.match(source, /HomeOutlined/, "the shell should import a recognizable dashboard shortcut icon");
  assert.match(source, /aria-label="返回控制台"/, "the icon-only control should remain accessible");
  assert.match(source, /onClick=\{\(\) => navigate\("dashboard"\)\}/, "the shortcut should activate the fixed dashboard route");
});
