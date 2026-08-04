import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("seal detail refreshes the row before reloading history and attachments", () => {
  const drawerStart = source.indexOf("<Drawer");
  assert.notEqual(drawerStart, -1, "seal detail drawer should exist");
  const drawerEnd = source.indexOf("</Drawer>", drawerStart);
  assert.notEqual(drawerEnd, -1, "seal detail drawer should close");
  const drawer = source.slice(drawerStart, drawerEnd);

  assert.match(
    drawer,
    /extra=\{detail \? <Button icon=\{<ReloadOutlined \/>\} onClick=\{\(\) => void refreshDetail\(\)\}>刷新<\/Button> : null\}/,
    "detail should reload the latest application row before history and attachment queries",
  );
});
