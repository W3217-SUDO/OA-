import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("seal draft edit keeps a direct entry to manage existing attachments", () => {
  assert.match(
    source,
    /editingApplication &&[\s\S]*?onClick=\{\(\) => \{[\s\S]*?openDetail\(editingApplication\)/,
    "editing a draft should expose the existing attachment manager without duplicating its file operations",
  );
});
