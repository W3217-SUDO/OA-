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
    writePage(target, page(name, `<pre>${escapeHtml(data.text || "（文件没有可显示的文字内容）")}</pre>`));
    return data.kind;
  } catch (error) {
    target.close?.();
    throw error;
  }
}
