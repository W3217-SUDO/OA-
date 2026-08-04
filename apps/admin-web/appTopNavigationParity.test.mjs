import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("top bar restores the legacy authorized system navigation entry", () => {
  assert.match(
    source,
    /<Dropdown[\s\S]*items: sideMenuItems[\s\S]*trigger=\{\["click"\]\}[\s\S]*系统导航/,
    "the top bar should expose the permission-filtered navigation tree as a click dropdown",
  );
  assert.match(
    source,
    /const item = flattenMenu\(sideMenuItems\)\.find[\s\S]*item\.children\?\.length[\s\S]*item\.link_url[\s\S]*openLegacyMenuItem\(item\)[\s\S]*navigate\(String\(key\)\)/,
    "top navigation should preserve nested-menu expansion and legacy/internal destinations",
  );
});
