import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("workspace restores the legacy active-page document title", () => {
  assert.match(
    source,
    /if \(!loggedIn\) return;\s*document\.title = resolveWorkspacePageLabel\(active, effectiveMenuItems\);/,
    "an authenticated workspace should synchronize the browser title to its active page",
  );
  assert.match(
    source,
    /\}, \[active, effectiveMenuItems, loggedIn\]\);/,
    "the title should follow route, menu-label, and session changes",
  );
});
