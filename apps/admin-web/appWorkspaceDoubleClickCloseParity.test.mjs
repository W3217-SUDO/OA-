import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/App.tsx", import.meta.url), "utf8");

test("workspace restores the legacy double-click close action for non-dashboard tabs", () => {
  assert.match(source, /onDoubleClick=\{\(event\) => \{/, "workspace labels should handle the legacy double-click gesture");
  assert.match(source, /if \(item\.key === "dashboard"\) return;/, "the fixed dashboard tab must ignore double-click close");
  assert.match(source, /closeOpenPage\(item\.key\)/, "double-click should reuse the standard tab-close flow");
});
