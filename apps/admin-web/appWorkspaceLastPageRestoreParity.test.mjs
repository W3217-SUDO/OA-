import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("workspace restores the legacy last-opened page without overriding an explicit route", () => {
  assert.match(source, /function readWorkspaceRouteFromLocation\(\)/, "the shell should centralize initial workspace restoration");
  assert.match(source, /const requestedRoute = new URLSearchParams\(window\.location\.search\)\.get\("page"\);[\s\S]*if \(requestedRoute\) return normalizeWorkspaceRoute\(requestedRoute\);/, "an explicit URL route must win over persisted state");
  assert.match(source, /localStorage\.getItem\("sunhold:last-page"\)/, "the active workspace page should survive a browser refresh");
  assert.match(source, /localStorage\.setItem\("sunhold:last-page", active\)/, "the active workspace page should be persisted as navigation changes");
  assert.match(source, /localStorage\.removeItem\("sunhold:last-page"\)/, "logout should clear the persisted workspace page");
});
