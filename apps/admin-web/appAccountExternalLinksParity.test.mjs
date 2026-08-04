import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("account menu restores the legacy public support links", () => {
  assert.match(source, /官网/, "the account menu should expose the official-site shortcut");
  assert.match(source, /forum\.idchien\.com/, "the account menu should preserve the legacy forum URL");
  assert.match(source, /doc\.idchien\.com/, "the account menu should preserve the legacy documentation URL");
  assert.match(source, /target="_blank"/, "external account links should open in a separate tab");
});
