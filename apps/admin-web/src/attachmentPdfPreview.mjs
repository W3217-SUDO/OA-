import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.mjs?worker&url";

const resourceLoaders = {
  cMapUrl: import.meta.glob("../node_modules/pdfjs-dist/cmaps/*.bcmap", { query: "?url&inline", import: "default" }),
  standardFontDataUrl: import.meta.glob("../node_modules/pdfjs-dist/standard_fonts/*.{pfb,ttf}", { query: "?url&inline", import: "default" }),
  wasmUrl: {
    "openjpeg.wasm": () => import("pdfjs-dist/wasm/openjpeg.wasm?url&inline").then((module) => module.default),
    "jbig2.wasm": () => import("pdfjs-dist/wasm/jbig2.wasm?url&inline").then((module) => module.default),
  },
};
const resources = Object.fromEntries(Object.entries(resourceLoaders).map(([kind, loaders]) => [
  kind,
  Object.fromEntries(Object.entries(loaders).map(([path, load]) => [
    path.split("/").pop(), load,
  ])),
]));

class LocalBinaryDataFactory {
  async fetch({ kind, filename }) {
    const load = resources[kind]?.[filename];
    if (!load) throw new Error(`PDF 本地资源未配置：${kind}/${filename}`);
    const url = await load();
    const response = await fetch(url);
    if (!response.ok) throw new Error(`PDF 本地资源加载失败：${filename} (${response.status})`);
    return new Uint8Array(await response.arrayBuffer());
  }
}

export const pdfPreviewBody = `<section class="pdf-preview">
  <nav class="pdf-controls" aria-label="PDF 翻页">
    <button type="button" data-pdf-prev title="上一页" aria-label="上一页" disabled>&larr;</button>
    <span data-pdf-counter aria-live="polite"></span>
    <button type="button" data-pdf-next title="下一页" aria-label="下一页" disabled>&rarr;</button>
  </nav>
  <div class="pdf-scroll"><p data-pdf-status role="status">正在加载 PDF...</p><canvas hidden aria-label="PDF 页面"></canvas></div>
</section>`;

export const pdfPreviewStyle = `
  .pdf-preview{display:flex;flex-direction:column;flex:1;min-height:0;min-width:0}
  .pdf-controls{display:flex;align-items:center;justify-content:center;gap:12px;flex-shrink:0;padding-bottom:8px}
  .pdf-controls [data-pdf-counter]{width:8em;max-width:calc(100% - 112px);min-width:0;text-align:center;font-variant-numeric:tabular-nums;white-space:nowrap}
  .pdf-controls button{width:44px;height:44px;border:1px solid #dfe2e7;border-radius:4px;background:#fff;font-size:20px;cursor:pointer}
  .pdf-controls button:disabled{color:#86909c;cursor:default}
  .pdf-scroll{flex:1;min-height:0;overflow:auto;overscroll-behavior:contain}
  .pdf-scroll canvas{display:block;background:#fff}
  .pdf-scroll canvas[hidden]{display:none}
  .pdf-scroll p{overflow-wrap:anywhere}
`;

const MAX_CANVAS_PIXELS = 8_000_000;

export async function renderAttachmentPdfPreview(target, blob) {
  const doc = target.document;
  const view = doc.defaultView;
  const root = doc.querySelector(".pdf-preview");
  if (!root) throw new Error("PDF 预览页面初始化失败");
  const scroll = root.querySelector(".pdf-scroll");
  const canvas = root.querySelector("canvas");
  const status = root.querySelector("[data-pdf-status]");
  const counter = root.querySelector("[data-pdf-counter]");
  const previous = root.querySelector("[data-pdf-prev]");
  const next = root.querySelector("[data-pdf-next]");
  let closed = false;
  let loadingTask;
  let pdf;
  let renderTask;
  let busy = false;
  let failed = false;
  let pendingResize = false;
  let renderedWidth = 0;
  let pageNumber = 1;

  const updateControls = () => {
    previous.disabled = busy || failed || !pdf || pageNumber <= 1;
    next.disabled = busy || failed || !pdf || pageNumber >= pdf.numPages;
  };
  const showError = (error) => {
    if (closed) return;
    failed = true;
    canvas.hidden = true;
    status.hidden = false;
    status.setAttribute("role", "alert");
    status.textContent = `PDF 预览失败：${error.message}`;
    updateControls();
  };

  // 单画布串行渲染，翻页后释放上一页资源，不累计长文档的画布。
  const renderPage = async () => {
    if (closed || busy || failed) return;
    busy = true;
    pendingResize = false;
    updateControls();
    canvas.hidden = true;
    status.hidden = false;
    status.textContent = `正在渲染第 ${pageNumber} 页...`;
    let page;
    try {
      page = await pdf.getPage(pageNumber);
      if (closed) return;
      renderedWidth = scroll.clientWidth;
      if (renderedWidth <= 0) throw new Error("PDF 预览容器宽度无效");
      const originalViewport = page.getViewport({ scale: 1 });
      const viewport = page.getViewport({ scale: renderedWidth / originalViewport.width });
      const pixelRatio = Math.min(view.devicePixelRatio, 2, Math.sqrt(MAX_CANVAS_PIXELS / (viewport.width * viewport.height)));
      canvas.width = Math.max(1, Math.floor(viewport.width * pixelRatio));
      canvas.height = Math.max(1, Math.floor(viewport.height * pixelRatio));
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("浏览器无法创建 PDF 画布");
      renderTask = page.render({ canvasContext: context, viewport, transform: [pixelRatio, 0, 0, pixelRatio, 0, 0] });
      await renderTask.promise;
      if (closed) return;
      counter.textContent = `${pageNumber} / ${pdf.numPages}`;
      canvas.setAttribute("aria-label", `PDF 第 ${pageNumber} 页，共 ${pdf.numPages} 页`);
      canvas.hidden = false;
      status.hidden = true;
    } catch (error) {
      pendingResize = false;
      throw error;
    } finally {
      renderTask = null;
      page?.cleanup();
      busy = false;
      updateControls();
      if (pendingResize && !closed) void renderPage().catch(showError);
    }
  };

  const observer = new ResizeObserver(() => {
    if (!pdf || closed || scroll.clientWidth === renderedWidth) return;
    if (busy) pendingResize = true;
    else void renderPage().catch(showError);
  });
  const destroy = async () => {
    if (closed) return;
    closed = true;
    observer.disconnect();
    renderTask?.cancel();
    canvas.width = 0;
    canvas.height = 0;
    await loadingTask?.destroy();
  };
  target.addEventListener("beforeunload", () => {
    void destroy().catch((error) => globalThis.reportError(error));
  }, { once: true });
  previous.addEventListener("click", () => {
    if (busy || failed || pageNumber <= 1) return;
    pageNumber -= 1;
    scroll.scrollTop = 0;
    void renderPage().catch(showError);
  });
  next.addEventListener("click", () => {
    if (busy || failed || pageNumber >= pdf.numPages) return;
    pageNumber += 1;
    scroll.scrollTop = 0;
    void renderPage().catch(showError);
  });

  try {
    const bytes = new Uint8Array(await blob.arrayBuffer());
    if (closed) return;
    GlobalWorkerOptions.workerSrc = workerUrl;
    loadingTask = getDocument({
      data: bytes,
      ownerDocument: doc,
      BinaryDataFactory: LocalBinaryDataFactory,
      useWorkerFetch: false,
      useSystemFonts: false,
      cMapPacked: true,
      stopAtErrors: true,
      canvasMaxAreaInBytes: MAX_CANVAS_PIXELS * 4,
      isEvalSupported: false,
    });
    pdf = await loadingTask.promise;
    if (closed) return;
    await renderPage();
    if (!closed) observer.observe(scroll);
  } catch (error) {
    if (closed) return;
    await destroy();
    throw error;
  }
}
