import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("seal detail exposes the legacy reopen-as-refresh action", () => {
  const drawerStart = source.indexOf("<Drawer");
  assert.notEqual(drawerStart, -1, "seal detail drawer should exist");
  const drawerEnd = source.indexOf("</Drawer>", drawerStart);
  assert.notEqual(drawerEnd, -1, "seal detail drawer should close");
  const drawer = source.slice(drawerStart, drawerEnd);

  assert.match(
    drawer,
    /extra=\{detail \? <Button icon=\{<ReloadOutlined \/>\} onClick=\{\(\) => void openDetail\(detail\)\}>刷新<\/Button> : null\}/,
    "detail should let users reload the existing history and attachment queries without reopening the list",
  );
});
