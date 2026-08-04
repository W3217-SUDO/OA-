import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("sidebar restores the legacy double-click reload for workspace pages", () => {
  assert.match(
    source,
    /function menuItemsWithDoubleClickReload\(/,
    "the shell should wrap sidebar leaves with a double-click reload label",
  );
  assert.match(
    source,
    /onDoubleClick=\{\(event\) => \{[\s\S]*?if \(item\.link_url \|\| item\.disabled\) return;[\s\S]*?onReload\(item\);/,
    "double-click must skip legacy links and reload the target workspace page",
  );
  assert.match(
    source,
    /const sidebarReloadableItems = menuItemsWithDoubleClickReload\(/,
    "the wrapped menu tree should be derived from the authorized sidebar items",
  );
  assert.match(
    source,
    /items=\{sidebarReloadableItems\}/,
    "the sidebar Menu should consume the wrapped double-click items",
  );
  assert.match(
    source,
    /setWorkspaceReloadKey\(\(value\) => value \+ 1\)/,
    "the double-click action should reuse the workspace page reload remount key",
  );
});
