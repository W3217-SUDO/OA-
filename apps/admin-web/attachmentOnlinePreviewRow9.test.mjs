import assert from "node:assert/strict";
import test from "node:test";

import { openAttachmentOnlinePreview } from "./src/attachmentOnlinePreview.mjs";

function popup() {
  const writes = [];
  return {
    writes,
    closed: false,
    document: { open() {}, write(value) { writes.push(value); }, close() {} },
    addEventListener() {},
    close() { this.closed = true; },
  };
}

test("XLSX preview opens a new page and escapes workbook content", async () => {
  const target = popup();
  const calls = [];
  const api = { get: async (url) => {
    calls.push(url);
    return { data: { kind: "xlsx", text: "<script>bad()</script>\t合同号" } };
  } };

  const kind = await openAttachmentOnlinePreview(api, { id: 9, original_name: "用印<申请>.xlsx" }, {
    openWindow: () => target,
  });

  assert.equal(kind, "xlsx");
  assert.deepEqual(calls, ["/attachments/9/preview"]);
  const html = target.writes.at(-1);
  assert.match(html, /用印&lt;申请&gt;\.xlsx/);
  assert.match(html, /&lt;script&gt;bad\(\)&lt;\/script&gt;\t合同号/);
  assert.doesNotMatch(html, /<script>bad\(\)<\/script>/);
});

test("PDF preview uses the authenticated download blob in the new page", async () => {
  const target = popup();
  const calls = [];
  const api = { get: async (url, options) => {
    calls.push([url, options]);
    if (url.endsWith("/preview")) return { data: { kind: "pdf" } };
    return { data: new Blob(["pdf"]) };
  } };

  await openAttachmentOnlinePreview(api, { id: 12, original_name: "盖章文件.pdf" }, {
    openWindow: () => target,
    createObjectURL: () => "blob:authenticated-preview",
    revokeObjectURL: () => {},
  });

  assert.deepEqual(calls, [
    ["/attachments/12/preview", undefined],
    ["/attachments/12/download", { responseType: "blob" }],
  ]);
  assert.match(target.writes.at(-1), /iframe src="blob:authenticated-preview"/);
});

test("legacy XLS preview renders escaped workbook cells as an HTML table", async () => {
  const target = popup();
  const api = { get: async () => ({ data: {
    kind: "workbook",
    sheets: [{ name: "费用<表>", rows: [["案号", "金额"], ["<script>bad()</script>", "100"]] }],
    truncated: false,
  } }) };

  const kind = await openAttachmentOnlinePreview(api, { id: 16, original_name: "历史费用.xls" }, { openWindow: () => target });

  assert.equal(kind, "workbook");
  const html = target.writes.at(-1);
  assert.match(html, /<table>/);
  assert.match(html, /费用&lt;表&gt;/);
  assert.match(html, /&lt;script&gt;bad\(\)&lt;\/script&gt;/);
  assert.doesNotMatch(html, /<script>bad\(\)<\/script>/);
});

test("unsupported files close the temporary page and preserve the server detail", async () => {
  const target = popup();
  const api = { get: async () => ({ data: { kind: "unsupported", detail: "格式不支持" } }) };

  await assert.rejects(
    openAttachmentOnlinePreview(api, { id: 15, original_name: "附件.bin" }, { openWindow: () => target }),
    (error) => error.response.data.detail === "格式不支持",
  );
  assert.equal(target.closed, true);
});
