import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("production runtime serves the completed Vite build", async () => {
  const packageJson = JSON.parse(
    await readFile(new URL("./package.json", import.meta.url), "utf8"),
  );

  assert.equal(packageJson.scripts.preview, "vite preview");
  assert.match(packageJson.scripts.build, /vite build/);
  assert.doesNotMatch(packageJson.scripts.preview, /vite(?:\s+--host|\s+dev)/);
});
