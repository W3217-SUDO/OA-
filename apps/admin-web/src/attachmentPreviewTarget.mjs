import { getENV } from "dingtalk-jsapi/lib/env.js";

function createInlinePreviewTarget() {
  const backdrop = document.createElement("div");
  backdrop.setAttribute("role", "dialog");
  backdrop.setAttribute("aria-label", "附件在线预览");
  backdrop.style.cssText = "position:fixed;inset:0;z-index:10000;background:#fff";

  const frame = document.createElement("iframe");
  frame.title = "附件在线预览内容";
  frame.style.cssText = "display:block;width:100%;height:100%;border:0";

  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.textContent = "关闭预览";
  closeButton.style.cssText = "position:absolute;top:8px;right:12px;z-index:1;padding:6px 12px;border:1px solid #dfe2e7;border-radius:4px;background:#fff;color:#1f2329;cursor:pointer";

  const cleanupListeners = [];
  let closed = false;
  const target = {
    get document() {
      return frame.contentDocument;
    },
    addEventListener(type, listener) {
      if (type === "beforeunload") cleanupListeners.push(listener);
    },
    close() {
      if (closed) return;
      closed = true;
      for (const listener of cleanupListeners) listener();
      document.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("pagehide", target.close);
      backdrop.remove();
    },
  };
  const onKeyDown = (event) => {
    if (event.key === "Escape") target.close();
  };
  closeButton.addEventListener("click", target.close);
  backdrop.append(frame, closeButton);
  document.body.append(backdrop);
  document.addEventListener("keydown", onKeyDown);
  window.addEventListener("pagehide", target.close);
  closeButton.focus();
  return target;
}

export function isInlineAttachmentPreviewEnvironment() {
  return getENV().platform !== "notInDingTalk";
}

export function createAttachmentPreviewTarget(openWindow) {
  if (openWindow) return openWindow();
  if (isInlineAttachmentPreviewEnvironment()) return createInlinePreviewTarget();
  return window.open("about:blank", "_blank");
}
