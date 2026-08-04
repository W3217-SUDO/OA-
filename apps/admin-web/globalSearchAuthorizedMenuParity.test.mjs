import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const appSource = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");
const searchSource = fs.readFileSync(new URL("./src/GlobalSearch.tsx", import.meta.url), "utf8");

test("global search exposes only authorized menu leaves and keeps legacy menu navigation", () => {
  assert.match(
    appSource,
    /<GlobalSearch[\s\S]*menuItems=\{sideMenuItems\}[\s\S]*onOpenMenu=\{[\s\S]*openLegacyMenuItem\(item\)[\s\S]*navigate\(item\.key\)/,
    "App should provide GlobalSearch with the permission-filtered menu and existing legacy-link handler",
  );
  assert.match(
    searchSource,
    /export function searchAuthorizedMenuItems\([\s\S]*!item\.children\?\.length[\s\S]*!item\.disabled/,
    "menu matching should include only clickable leaf entries",
  );
  assert.match(
    searchSource,
    /onChange=\{\(event\) => handleQueryChange\(event\.target\.value\)\}/,
    "typing should update the menu results without a backend request",
  );
  assert.match(
    searchSource,
    /if \(onOpenMenu\) onOpenMenu\(item\.item\);[\s\S]*else onNavigate\(item\.item\.key\);/,
    "a selected menu result should use the supplied legacy-link callback or internal router",
  );
});
