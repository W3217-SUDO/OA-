import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("seal detail refresh replaces the stale row before reloading history and files", () => {
  assert.match(
    source,
    /const refreshDetail = async \(\) => \{[\s\S]*?const latestRows = await load\(\);[\s\S]*?latestRows\?\.find\([\s\S]*?await openDetail\(latestRow\);/,
    "refresh should use the existing applications list response to refresh status and approval fields",
  );
  assert.match(
    source,
    /extra=\{detail \? <Button icon=\{<ReloadOutlined \/>\} onClick=\{\(\) => void refreshDetail\(\)\}>刷新<\/Button> : null\}/,
    "the detail refresh button must use the fresh-row path",
  );
});
