import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("workspace keeps the legacy dashboard tab permanently open", () => {
  assert.match(
    source,
    /closable: item\.key !== "dashboard"/,
    "the initial dashboard tab must remain non-closable after other workspace pages open",
  );
});
