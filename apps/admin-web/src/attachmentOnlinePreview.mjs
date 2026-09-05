import mammoth from "mammoth";
import * as XLSX from "xlsx";

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#39;");

const page = (title, body, extraStyle = "") => `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <style>
    html,body{margin:0;min-height:100%;background:#f5f6f8;color:#1f2329;font-family:Arial,"Microsoft YaHei",sans-serif}
    header{position:sticky;top:0;padding:12px 20px;background:#fff;border-bottom:1px solid #dfe2e7;font-weight:600;overflow-wrap:anywhere;z-index:10}
    main{box-sizing:border-box;min-height:calc(100vh - 49px);padding:20px}
    pre{box-sizing:border-box;max-width:1200px;margin:0 auto;padding:24px;background:#fff;border:1px solid #dfe2e7;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65}
    iframe{display:block;width:100%;height:calc(100vh - 89px);border:0;background:#fff}
    img{display:block;max-width:100%;max-height:calc(100vh - 89px);margin:0 auto;background:#fff}
    .status{max-width:1200px;margin:0 auto;padding:24px;background:#fff;border:1px solid #dfe2e7}
    .docx-preview{max-width:900px;margin:0 auto;padding:48px 64px;background:#fff;border:1px solid #dfe2e7;box-shadow:0 2px 8px rgba(0,0,0,.04);line-height:1.8;font-size:14px;color:#1f2329;min-height:600px}
    .docx-preview h1{font-size:24px;font-weight:700;margin:24px 0 16px;border-bottom:2px solid #eee;padding-bottom:8px}
    .docx-preview h2{font-size:20px;font-weight:700;margin:20px 0 12px}
    .docx-preview h3{font-size:17px;font-weight:700;margin:16px 0 10px}
    .docx-preview h4{font-size:15px;font-weight:700;margin:14px 0 8px}
    .docx-preview p{margin:10px 0;text-indent:0}
    .docx-preview table{border-collapse:collapse;margin:12px 0;width:100%}
    .docx-preview th,.docx-preview td{border:1px solid #d0d5dd;padding:8px 12px;vertical-align:top;text-align:left}
    .docx-preview th{background:#f5f7fa;font-weight:600}
    .docx-preview ul,.docx-preview ol{margin:10px 0;padding-left:28px}
    .docx-preview li{margin:4px 0}
    .docx-preview strong{font-weight:700}
    .docx-preview em{font-style:italic}
    .docx-preview u{text-decoration:underline}
    .docx-preview strike{text-decoration:line-through}
    .docx-preview blockquote{border-left:3px solid #d0d5dd;margin:12px 0;padding:8px 16px;color:#4e5969;background:#fafbfc}
    .docx-preview a{color:#165dff;text-decoration:none}
    .docx-preview a:hover{text-decoration:underline}
    .docx-preview img{max-width:100%;height:auto}
    .docx-preview hr{border:none;border-top:1px solid #e5e6eb;margin:16px 0}
    .xlsx-preview{max-width:100%;margin:0 auto;background:#fff;border:1px solid #dfe2e7;overflow:auto;max-height:calc(100vh - 120px)}
    .xlsx-tabs{display:flex;gap:4px;padding:8px 12px 0;background:#f5f6f8;border-bottom:1px solid #dfe2e7;flex-wrap:wrap}
    .xlsx-tab{padding:8px 16px;border:1px solid #dfe2e7;border-bottom:none;border-radius:4px 4px 0 0;cursor:pointer;background:#fff;font-size:13px;color:#4e5969;user-select:none}
    .xlsx-tab.active{background:#fff;color:#165dff;font-weight:600;border-color:#165dff;border-bottom:2px solid #fff;margin-bottom:-1px;position:relative;z-index:1}
    .xlsx-tab:hover{color:#165dff}
    .xlsx-sheet-container{padding:0;overflow:auto}
    .xlsx-table{border-collapse:collapse;width:100%;font-size:12px;font-family:Arial,"Microsoft YaHei",sans-serif}
    .xlsx-table th,.xlsx-table td{border:1px solid #d0d5dd;padding:4px 8px;white-space:nowrap;max-width:300px;overflow:hidden;text-overflow:ellipsis;text-align:left;vertical-align:top}
    .xlsx-table th{background:#f5f7fa;font-weight:600;position:sticky;top:0;z-index:1;color:#1f2329}
    .xlsx-table tr:nth-child(even) td{background:#fafbfc}
    .xlsx-table td:hover{background:#e8f3ff;white-space:normal}
    .xlsx-empty{padding:40px;text-align:center;color:#86909c}
    .xlsx-info{padding:8px 12px;background:#f5f7fa;border-top:1px solid #dfe2e7;font-size:12px;color:#4e5969}
    .render-error{max-width:900px;margin:0 auto 12px;padding:16px 20px;background:#fff7e8;border:1px solid #ffd591;color:#d46b08;border-radius:4px}
    ${extraStyle}
  </style>
</head>
<body><header>${escapeHtml(title)}</header><main>${body}</main></body>
</html>`;

const writePage = (target, html) => {
  target.document.open();
  target.document.write(html);
  target.document.close();
};

async function renderDocxFromBlob(blob) {
  const arrayBuffer = await blob.arrayBuffer();
  const result = await mammoth.convertToHtml({ arrayBuffer });
  return result.value;
}

function renderXlsxFromArrayBuffer(arrayBuffer, fileName) {
  const workbook = XLSX.read(arrayBuffer, { type: "array" });
  const sheetNames = workbook.SheetNames;
  if (!sheetNames.length) {
    return { html: '<div class="xlsx-empty">（该 Excel 文件没有可显示的工作表）</div>', sheetCount: 0, rowCount: 0 };
  }

  const sheetTables = sheetNames.map((name) => {
    const sheet = workbook.Sheets[name];
    const html = XLSX.utils.sheet_to_html(sheet, { id: `sheet-${name}`, editable: false });
    return { name, html };
  });

  const totalRows = sheetTables.reduce((sum, sheet) => {
    const match = sheet.html.match(/<tr/g);
    return sum + (match ? match.length : 0);
  }, 0);

  const tabsHtml = sheetNames.map((name, idx) =>
    `<div class="xlsx-tab ${idx === 0 ? "active" : ""}" data-sheet="${escapeHtml(name)}" onclick="switchSheet(this)">${escapeHtml(name)}</div>`
  ).join("");

  const sheetsHtml = sheetTables.map((sheet, idx) =>
    `<div class="xlsx-sheet-container" data-sheet-content="${escapeHtml(sheet.name)}" style="${idx === 0 ? "" : "display:none"}">${sheet.html.replace(/<table/, '<table class="xlsx-table"')}</div>`
  ).join("");

  const infoHtml = `<div class="xlsx-info">共 ${sheetNames.length} 个工作表，约 ${totalRows} 行数据</div>`;

  const fullHtml = `
    <div class="xlsx-tabs">${tabsHtml}</div>
    <div class="xlsx-preview">${sheetsHtml}</div>
    ${infoHtml}
    <script>
      function switchSheet(tabEl) {
        const sheetName = tabEl.getAttribute('data-sheet');
        document.querySelectorAll('.xlsx-tab').forEach(t => t.classList.remove('active'));
        tabEl.classList.add('active');
        document.querySelectorAll('[data-sheet-content]').forEach(el => {
          el.style.display = el.getAttribute('data-sheet-content') === sheetName ? '' : 'none';
        });
      }
    <\/script>
  `;

  return { html: fullHtml, sheetCount: sheetNames.length, rowCount: totalRows };
}

export async function openAttachmentOnlinePreview(api, attachment, options = {}) {
  const openWindow = options.openWindow || (() => window.open("about:blank", "_blank"));
  const createObjectURL = options.createObjectURL || ((blob) => URL.createObjectURL(blob));
  const revokeObjectURL = options.revokeObjectURL || ((url) => URL.revokeObjectURL(url));
  const target = openWindow();
  if (!target) throw new Error("浏览器阻止了新标签页，请允许本站打开新标签页后重试");

  const name = attachment.original_name || "附件预览";
  const suffix = String(name).split(".").pop()?.toLowerCase() || "";
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
    if (data.kind === "docx") {
      const response = await api.get(`/attachments/${attachment.id}/download`, { responseType: "blob" });
      try {
        const html = await renderDocxFromBlob(response.data);
        const body = `<div class="docx-preview">${html || '<p style="color:#86909c">（文件没有可显示的内容）</p>'}</div>`;
        writePage(target, page(name, body));
      } catch (renderError) {
        const fallbackText = data.text || "（文件没有可显示的文字内容）";
        const body = `<div class="render-error">渲染 Word 排版失败，以下为纯文本预览：${renderError.message || ""}</div><pre>${escapeHtml(fallbackText)}</pre>`;
        writePage(target, page(name, body));
      }
      return "docx";
    }
    if (data.kind === "xlsx" || suffix === "xls" || suffix === "xlsx") {
      const response = await api.get(`/attachments/${attachment.id}/download`, { responseType: "blob" });
      try {
        const arrayBuffer = await response.data.arrayBuffer();
        const result = renderXlsxFromArrayBuffer(arrayBuffer, name);
        writePage(target, page(name, result.html));
      } catch (renderError) {
        const fallbackText = data.text || "（文件没有可显示的内容）";
        const body = `<div class="render-error">渲染 Excel 表格失败，以下为纯文本预览：${renderError.message || ""}</div><pre>${escapeHtml(fallbackText)}</pre>`;
        writePage(target, page(name, body));
      }
      return "xlsx";
    }
    writePage(target, page(name, `<pre>${escapeHtml(data.text || "（文件没有可显示的文字内容）")}</pre>`));
    return data.kind;
  } catch (error) {
    target.close?.();
    throw error;
  }
}
