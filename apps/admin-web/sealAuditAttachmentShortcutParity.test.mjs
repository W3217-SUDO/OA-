import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("seal approval action keeps the legacy same-entry attachment inspection", () => {
  assert.match(
    source,
    /action\?\.type === "approve"[\s\S]*?onClick=\{\(\) => \{[\s\S]*?openDetail\(action\.row\)/,
    "approval should expose a direct link to inspect the application files before deciding",
  );
});
