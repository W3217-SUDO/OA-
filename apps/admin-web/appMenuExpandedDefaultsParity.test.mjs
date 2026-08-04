import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("menu tree restores the legacy expanded default after authorized menus load", () => {
  assert.match(source, /function menuKeysWithChildren\(items: NavItem\[\]\): string\[\]/, "the shell should identify expandable menu nodes");
  assert.match(source, /const \[openMenuKeys, setOpenMenuKeys\] = useState<string\[\]>\(\[\]\)/, "the shell should retain user-controlled menu state");
  assert.match(source, /const defaults = menuKeysWithChildren\(effectiveMenuItems\)/, "menu defaults should be derived from the authorized configuration");
  assert.match(source, /setOpenMenuKeys\(\(current\) => current\.length \? current : defaults\)/, "defaults should apply only when the menu has not been opened or collapsed by the user");
});
