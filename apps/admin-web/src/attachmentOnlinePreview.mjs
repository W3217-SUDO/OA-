const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#39;");

const page = (title, body) => `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <style>
    html,body{margin:0;min-height:100%;background:#f5f6f8;color:#1f2329;font-family:Arial,"Microsoft YaHei",sans-serif}
    header{position:sticky;top:0;padding:12px 20px;background:#fff;border-bottom:1px solid #dfe2e7;font-weight:600;overflow-wrap:anywhere}
    main{box-sizing:border-box;min-height:calc(100vh - 49px);padding:20px}
    pre{box-sizing:border-box;max-width:1200px;margin:0 auto;padding:24px;background:#fff;border:1px solid #dfe2e7;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65}
    section{margin:0 0 20px;background:#fff;border:1px solid #dfe2e7}
    h2{position:sticky;left:0;margin:0;padding:10px 12px;font-size:15px;border-bottom:1px solid #dfe2e7}
    .sheet{overflow:auto;max-height:calc(100vh - 150px)}
    table{border-collapse:collapse;min-width:100%;font-size:13px}
    td{min-width:96px;max-width:360px;padding:7px 9px;border-right:1px solid #e5e7eb;border-bottom:1px solid #e5e7eb;white-space:pre-wrap;overflow-wrap:anywhere;vertical-align:top}
    tr:first-child td{position:sticky;top:0;background:#f5f7fa;font-weight:600}
    .notice{padding:10px 12px;background:#fff8e6;border:1px solid #ffd591;margin-bottom:16px}
    iframe{display:block;width:100%;height:calc(100vh - 89px);border:0;background:#fff}
    img{display:block;max-width:100%;max-height:calc(100vh - 89px);margin:0 auto;background:#fff}
    .status{max-width:1200px;margin:0 auto;padding:24px;background:#fff;border:1px solid #dfe2e7}
  </style>
</head>
<body><header>${escapeHtml(title)}</header><main>${body}</main></body>
</html>`;

const writePage = (target, html) => {
  target.document.open();
  target.document.write(html);
  target.document.close();
};

const workbookPage = (data) => {
  const notice = data.truncated
    ? '<div class="notice">文件内容较多，当前页面仅显示前部分行列。</div>'
    : "";
  const sheets = (data.sheets || []).map((sheet) => {
    const rows = (sheet.rows || []).map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("");
    return `<section><h2>${escapeHtml(sheet.name || "工作表")}</h2><div class="sheet"><table><tbody>${rows || '<tr><td>（空工作表）</td></tr>'}</tbody></table></div></section>`;
  }).join("");
  return `${notice}${sheets || '<div class="status">（工作簿没有可显示的内容）</div>'}`;
};

export async function openAttachmentOnlinePreview(api, attachment, options = {}) {
  const openWindow = options.openWindow || (() => window.open("about:blank", "_blank"));
  const createObjectURL = options.createObjectURL || ((blob) => URL.createObjectURL(blob));
  const revokeObjectURL = options.revokeObjectURL || ((url) => URL.revokeObjectURL(url));
  const target = openWindow();
  if (!target) throw new Error("浏览器阻止了新标签页，请允许本站打开新标签页后重试");

  const name = attachment.original_name || "附件预览";
  writePage(target, page(name, '<div class="status">正在加载文件...</div>'));
  try {
    const { data } = await api.get(`/attachments/${attachment.id}/preview`);
    if (data.kind === "unsupported") {
      const error = new Error(data.detail || "当前文件格式暂不支持在线预览");
      error.response = { data: { detail: error.message } };
      throw error;
    }
    if (data.kind === "image" || data.kind === "pdf") {
      const response = await api.get(`/attachments/${attachment.id}/download`, { responseType: "blob" });
      const url = createObjectURL(response.data);
      const body = data.kind === "image"
        ? `<img src="${escapeHtml(url)}" alt="${escapeHtml(name)}">`
        : `<iframe src="${escapeHtml(url)}" title="${escapeHtml(name)}"></iframe>`;
      writePage(target, page(name, body));
      target.addEventListener?.("beforeunload", () => revokeObjectURL(url), { once: true });
      return data.kind;
    }
    if (data.kind === "workbook") {
      writePage(target, page(name, workbookPage(data)));
      return data.kind;
    }
    writePage(target, page(name, `<pre>${escapeHtml(data.text || "（文件没有可显示的文字内容）")}</pre>`));
    return data.kind;
  } catch (error) {
    target.close?.();
    throw error;
  }
}
