import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("menu tree keeps only the active branch open by default", () => {
  assert.match(source, /function menuKeysWithChildren\(items: NavItem\[\]\): string\[\]/, "the shell should still identify expandable menu nodes");
  assert.match(source, /export function normalizeOpenMenuKeys\(/, "the shell should normalize open menu branches");
  assert.match(source, /const \[openMenuKeys, setOpenMenuKeys\] = useState<string\[\]>\(\[\]\)/, "the shell should retain user-controlled menu state");
  assert.match(source, /setOpenMenuKeys\(ancestors\)/, "the active route should open only its ancestor chain");
  assert.doesNotMatch(source, /setOpenMenuKeys\(\(current\) => current\.length \? current : defaults\)/, "the shell should not restore the old expand-all default");
});

test("menu open-change keeps only the newly focused ancestor chain", () => {
  assert.match(
    source,
    /return \[\.\.\.focusPath, focusKey\]\.filter\(\(key\) => nextKeys\.includes\(key\)\)/,
    "open menu keys should be reduced to the focused ancestor chain instead of retaining sibling submenus",
  );
  assert.doesNotMatch(source, /return nextKeys\.filter\(\(key\) => \{[\s\S]*path\[0\] === rootKey[\s\S]*\}\)/);
});

test("all nested sidebar entries receive the legacy list icon", () => {
  assert.match(source, /depth = 0/);
  assert.match(source, /menuItemsWithDoubleClickReload\(item\.children, onReload, depth \+ 1\)/);
  assert.match(source, /icon: item\.icon \|\| \(depth > 0 \? <UnorderedListOutlined \/> : undefined\)/);
});

test("expanded sidebar leaves enough room for full nested labels", () => {
  assert.match(source, /<Sider[\s\S]*width=\{280\}/);
  assert.match(source, /<Menu[\s\S]*inlineIndent=\{16\}/);
});
