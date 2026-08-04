import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("seal approval action keeps the legacy read-only application context", () => {
  assert.match(
    source,
    /action\?\.type === "approve"[\s\S]*?Descriptions[\s\S]*?action\.row\.serial_no[\s\S]*?action\.row\.title[\s\S]*?action\.row\.customer/,
    "approval should show the request context before the decision form",
  );
});
