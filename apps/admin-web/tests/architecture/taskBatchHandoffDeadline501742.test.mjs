import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");

test("501742：批量交接窗口有选填的任务期限，提交时带上，缩短的列出来", () => {
  const modals = read("../../src/tp/TaskActionModals.tsx");
  assert.match(modals, /label="任务期限（选填）"\s+name="end_at"/);
  assert.doesNotMatch(modals.slice(modals.indexOf('label="任务期限（选填）"'), modals.indexOf('label="任务期限（选填）"') + 120), /required/);
  const page = read("../../src/tp/TaskCenterPage.tsx");
  assert.match(page, /end_at: values\.end_at \? values\.end_at\.format\("YYYY-MM-DDTHH:mm:ss"\) : undefined/);
  assert.match(page, /data\.deadline_limited/);
});

test("501742：所有带时间的日期选择手机上都不超出屏幕", () => {
  const shared = read("../../src/components/common/dateTimePopup.ts");
  assert.match(shared, /root: "oa-datetime-popup"/);
  assert.match(shared, /getPopupContainer: \(\) => document\.body/);
  for (const [path, count] of [
    ["../../src/tp/TaskActionModals.tsx", 2], ["../../src/tp/TaskCreateModal.tsx", 2], ["../../src/VipTaskCenterPage.tsx", 3],
    ["../../src/CommunicationLogPage.tsx", 1], ["../../src/legal/CaseCenterPage.tsx", 5],
  ]) {
    const source = read(path);
    assert.equal(source.match(/showTime/g)?.length, count, path);
    assert.equal(source.match(/\{\.\.\.DATETIME_POPUP_PROPS\}/g)?.length, count, path);
  }
  const styles = read("../../src/styles.css");
  const block = styles.slice(styles.indexOf("501742"));
  assert.match(block, /\.oa-datetime-popup\.ant-picker-dropdown \{[^}]*position: fixed !important/);
  assert.match(block, /max-height: calc\(100vh - 16px\)/);
  assert.doesNotMatch(block, /color-mix|:has\(|@container|dvh/); // 钉钉手机内核 Chrome 100 不支持
});
