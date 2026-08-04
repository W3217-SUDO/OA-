import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("sidebar keeps legacy menu-permission filtering and blocked-route guard", () => {
  assert.match(
    source,
    /function filterMenuByGrantedKeys\(items: NavItem\[\], grantedKeys: Set<string>\)/,
    "the shell should filter the menu tree by granted menu keys",
  );
  assert.match(
    source,
    /item\.key !== "dashboard" && !grantedKeys\.has\(item\.key\) && !children\.length/,
    "the dashboard entry should survive while unauthorized leaves are dropped",
  );
  assert.match(
    source,
    /sessionUser\?\.menu_keys \|\| \["user-center"\]/,
    "non-admin sidebar grants should come from the stored user menu keys",
  );
  assert.match(
    source,
    /const pageAllowed =/,
    "the shell should compute a route-level permission guard",
  );
  assert.match(
    source,
    /<h2>无权访问<\/h2>/,
    "an unauthorized route should render an explicit blocked state",
  );
  assert.match(
    source,
    /返回控制台/,
    "the blocked state should offer a return-to-console action",
  );
});
