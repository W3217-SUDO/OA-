// BUG20261102010：用印中心页签条隐藏，旧系统用印记录要有看得见的入口和返回按钮。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const page = fs.readFileSync(new URL("../src/seal/SealCenterPage.tsx", import.meta.url), "utf8");

test("用印列表查询区有“旧系统用印记录”入口，旧记录页有返回按钮", () => {
  assert.match(page, /<Button onClick=\{\(\) => setTab\("legacy"\)\}>旧系统用印记录<\/Button>/);
  assert.match(page, /tab === "legacy" \? <Button onClick=\{\(\) => setTab\(tabFromView\(initialView\)\)\}>返回用印申请<\/Button>/);
  assert.match(page, /tab === "legacy" \? \(\s*<LegacySealRecords \/>/);
});
