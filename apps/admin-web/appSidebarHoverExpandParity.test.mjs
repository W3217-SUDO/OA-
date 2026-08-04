import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("sidebar restores the legacy expand-on-hover behavior", () => {
  assert.match(source, /sidebarHoverExpanded/, "the shell should track a temporary hover-expanded state");
  assert.match(source, /onMouseEnter=\{\(\) => collapsed && setSidebarHoverExpanded\(true\)\}/, "hovering a collapsed sidebar should expand it");
  assert.match(source, /onMouseLeave=\{\(\) => setSidebarHoverExpanded\(false\)\}/, "leaving the sidebar should restore its collapsed presentation");
  assert.match(source, /collapsed=\{collapsed && !sidebarHoverExpanded\}/, "hover expansion must not overwrite the saved collapse preference");
});
