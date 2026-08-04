import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/NotificationCenter.tsx", import.meta.url), "utf8");

test("notification badge restores the legacy thirty-second polling cadence", () => {
  assert.match(source, /const timer = window\.setInterval\(load, 30000\)/, "the notification badge should refresh at the legacy thirty-second cadence");
  assert.match(source, /window\.clearInterval\(timer\)/, "unmounting should still clear the polling timer");
});
