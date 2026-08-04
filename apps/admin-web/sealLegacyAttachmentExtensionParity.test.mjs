import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("seal upload validation keeps the legacy official-document attachment extensions", () => {
  const extensionSet = source.match(/const sealUploadExtensions = new Set\(\[([\s\S]*?)\]\)/)?.[1] || "";

  for (const extension of [".bmp", ".gif", ".ini", ".conf", ".eml"]) {
    assert.match(
      extensionSet,
      new RegExp(`"\\${extension}"`),
      `legacy seal uploads should accept ${extension}`,
    );
  }
});
