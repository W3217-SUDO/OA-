import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("sidebar avatar restores the legacy profile shortcut", () => {
  assert.match(source, /className="avatar"\s+role="button"\s+tabIndex=\{0\}/, "the sidebar avatar should be keyboard reachable");
  assert.match(source, /aria-label="打开个人资料"/, "the sidebar avatar should describe its destination");
  assert.match(source, /onClick=\{\(\) => navigate\(accountProfileRoute\)\}/, "clicking the sidebar avatar should open the authorized profile route");
  assert.match(source, /if \(event\.key === "Enter" \|\| event\.key === " "\)/, "keyboard activation should match the other shell shortcuts");
});
