import assert from "node:assert/strict";
import { renderStructuredWorkbook } from "./attachmentOnlinePreview.mjs";

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
