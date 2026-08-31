import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./src/TaskCenterPage.tsx", import.meta.url), "utf8");

test("personal, created, and collaborating active tabs include the case-task display status", () => {
  const occurrences = source.match(/statuses: \["待接收", "待处理", "处理中", "进行中", "已逾期"\]/g) || [];
  assert.equal(occurrences.length, 2);
  assert.match(source, /statuses: \["处理中", "进行中", "已逾期"\]/);
});
