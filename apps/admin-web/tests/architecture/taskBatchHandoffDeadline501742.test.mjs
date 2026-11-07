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

test("501742：批量和单条转交的日期面板手机上不超出屏幕", () => {
  const modals = read("../../src/tp/TaskActionModals.tsx");
  assert.equal(modals.match(/<DatePicker showTime \{\.\.\.DATETIME_POPUP_PROPS\}/g)?.length, 2);
  assert.match(modals, /getPopupContainer: \(\) => document\.body/);
  const styles = read("../../src/styles.css");
  const block = styles.slice(styles.indexOf("501742"));
  assert.match(block, /\.oa-datetime-popup\.ant-picker-dropdown \{[^}]*position: fixed !important/);
  assert.match(block, /max-height: calc\(100vh - 16px\)/);
  assert.doesNotMatch(block, /color-mix|:has\(|@container|dvh/); // 钉钉手机内核 Chrome 100 不支持
});
