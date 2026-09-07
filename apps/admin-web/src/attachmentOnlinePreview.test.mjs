import assert from "node:assert/strict";
import { openAttachmentOnlinePreview, renderStructuredWorkbook } from "./attachmentOnlinePreview.mjs";

const html = renderStructuredWorkbook([
  { name: "用印文件", rows: [["案件编号", "客户名称"], ["CODEX-001", "中文客户"]] },
]);

assert.match(html, /用印文件/);
assert.match(html, /案件编号/);
assert.match(html, /中文客户/);
assert.doesNotMatch(html, /&lt;td&gt;/);

const escaped = renderStructuredWorkbook([
  { name: "<script>", rows: [["<img src=x onerror=alert(1)>"]] },
]);
assert.match(escaped, /&lt;script&gt;/);
assert.match(escaped, /&lt;img src=x onerror=alert\(1\)&gt;/);
assert.doesNotMatch(escaped, /<img src=x/);

let renderedPage = "";
const target = {
  document: {
    open() {},
    write(html) { renderedPage = html; },
    close() {},
  },
};
const calls = [];
const api = {
  async get(url) {
    calls.push(url);
    return { data: { kind: "workbook", sheets: [{ name: "原始数据", rows: [["名称", "金额"], ["测试", 100]] }], truncated: false } };
  },
};
assert.equal(
  await openAttachmentOnlinePreview(api, { id: 42, original_name: "原始表格.xls" }, { openWindow: () => target }),
  "workbook",
);
assert.deepEqual(calls, ["/attachments/42/preview"]);
assert.match(renderedPage, /原始数据/);
assert.match(renderedPage, /测试/);
assert.doesNotMatch(renderedPage, /view\.officeapps\.live\.com/);
