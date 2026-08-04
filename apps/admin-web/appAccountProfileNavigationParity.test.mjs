import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("top account menu restores the legacy personal-profile shortcut", () => {
  assert.match(
    source,
    /const accountProfileRoute = grantedMenuKeys\.has\("user-account"\) \? "user-account" : "user-center";/,
    "profile navigation should prefer the explicit account grant while retaining the standard user-center fallback",
  );
  assert.match(
    source,
    /<Dropdown[\s\S]*key: "profile", label: "个人资料"[\s\S]*key: "logout", label: "退出"[\s\S]*navigate\(accountProfileRoute\)[\s\S]*logout\(\)/,
    "the top account menu should provide the old personal-profile shortcut alongside logout",
  );
});
