import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("workspace restores the legacy current-page refresh action", () => {
  assert.match(source, /ReloadOutlined/, "the shell should expose a recognizable workspace refresh icon");
  assert.match(source, /const \[workspaceReloadKey, setWorkspaceReloadKey\] = useState\(0\);/, "refresh state should remount only the active workspace page");
  assert.match(source, /onClick=\{\(\) => setWorkspaceReloadKey\(\(value\) => value \+ 1\)\}/, "the refresh action should advance the workspace remount key");
  assert.match(source, /<PageLoadBoundary key=\{`\$\{active\}:\$\{workspaceReloadKey\}`\}>/, "the active page boundary should receive the refresh key");
});
