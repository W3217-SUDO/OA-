/** Print only the rendered finance document in an isolated same-origin window. */
export function printFinanceDocument(selector = ".finance-payment-print-sheet, .payment-print-document"): boolean {
  const source = document.querySelector<HTMLElement>(selector);
  if (!source) return false;
  const popup = window.open("", "_blank", "width=1100,height=800");
  if (!popup) {
    window.print();
    return false;
  }
  const styles = Array.from(document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]'))
    .map((link) => `<link rel="stylesheet" href="${link.href}">`)
    .join("");
  popup.document.write(`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>付款申请单</title>${styles}<style>html,body{margin:0;background:#fff;color:#111}body{padding:24px}.finance-payment-print-sheet,.payment-print-document{max-width:none!important;width:100%!important;margin:0!important}.ant-btn,.finance-payment-package-actions,.payment-screen-actions{display:none!important}@media print{body{padding:0}}</style></head><body>${source.outerHTML}</body></html>`);
  popup.document.close();
  popup.focus();
  window.setTimeout(() => { popup.print(); popup.close(); }, 250);
  return true;
}
