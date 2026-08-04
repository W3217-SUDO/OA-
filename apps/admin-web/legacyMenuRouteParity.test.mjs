import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

const sliceBetween = (text, startMarker, endMarker, label) => {
  const start = text.indexOf(startMarker);
  assert.notEqual(start, -1, `${label} start marker should exist`);
  const end = text.indexOf(endMarker, start + startMarker.length);
  assert.notEqual(end, -1, `${label} end marker should exist`);
  return text.slice(start, end);
};

const navTypes = sliceBetween(source, "type NavItem = {", "const menuItems", "navigation types");
const configuredMenuItems = sliceBetween(source, "function configuredMenuItems", "function flattenMenu", "configured menus");
const legacyMenuHandler = sliceBetween(source, "const openLegacyMenuItem", "  useEffect(() => {", "legacy menu handler");
const menuClickHandler = sliceBetween(source, "onClick={({ key }) => {", "          />", "menu click handler");

test("legacy navigation config keeps old LinkUrl/MenuTypeId fields", () => {
  assert.match(navTypes, /link_url\?: string;/, "NavItem should carry normalized legacy link_url");
  assert.match(navTypes, /LinkUrl\?: string;/, "NavConfig should accept legacy PascalCase LinkUrl");
  assert.match(navTypes, /MenuTypeId\?: number;/, "NavConfig should accept legacy PascalCase MenuTypeId");
  assert.match(navTypes, /open_target\?: string;/, "legacy menus should carry an optional target");
});

test("configured menus do not hide authorized system-users and only disable legacy menus without links", () => {
  assert.doesNotMatch(
    configuredMenuItems,
    /item\.key !== "system-users"/,
    "system-users must not be hard-filtered by the frontend when the backend grants it",
  );
  assert.match(
    configuredMenuItems,
    /const linkUrl = item\.link_url \|\| item\.LinkUrl \|\| "";/,
    "configured menus should normalize old LinkUrl into linkUrl",
  );
  assert.match(
    configuredMenuItems,
    /disabled: item\.key\.startsWith\("legacy-menu-"\) && !linkUrl/,
    "legacy menu leaves with an old LinkUrl should stay clickable",
  );
});

test("menu clicks open legacy LinkUrl entries instead of routing them through React pages", () => {
  assert.match(legacyMenuHandler, /window\.open\(rawUrl, target, "noopener,noreferrer"\)/);
  assert.match(legacyMenuHandler, /window\.location\.assign\(url\)/);
  assert.match(menuClickHandler, /if \(item\.link_url\) \{[\s\S]*openLegacyMenuItem\(item\);[\s\S]*return;[\s\S]*\}/);
});
