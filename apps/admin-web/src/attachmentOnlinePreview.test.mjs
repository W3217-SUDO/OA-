import assert from "node:assert/strict";
import { buildOfficeOnlineViewerUrl, openAttachmentOnlinePreview, renderStructuredWorkbook } from "./attachmentOnlinePreview.mjs";

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

const sourceUrl = "http://oa.example.test/api/v1/public/attachments/office-preview/signed-token";
assert.equal(
  buildOfficeOnlineViewerUrl(sourceUrl),
  `https://view.officeapps.live.com/op/view.aspx?src=${encodeURIComponent(sourceUrl)}`,
);

let replacedUrl = "";
const target = {
  document: {
    open() {},
    write() {},
    close() {},
  },
  location: { replace(url) { replacedUrl = url; } },
};
const calls = [];
const api = {
  async get(url) {
    calls.push(url);
    return { data: { kind: "office", source_url: "/api/v1/public/attachments/office-preview/signed-token" } };
  },
};
assert.equal(
  await openAttachmentOnlinePreview(api, { id: 42, original_name: "原始表格.xlsx" }, { openWindow: () => target, origin: "http://oa.example.test" }),
  "office",
);
assert.deepEqual(calls, ["/attachments/42/office-preview"]);
assert.equal(replacedUrl, buildOfficeOnlineViewerUrl(sourceUrl));
