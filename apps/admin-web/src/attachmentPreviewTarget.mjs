import { getENV } from "dingtalk-jsapi/lib/env.js";

function createInlinePreviewTarget() {
  const backdrop = document.createElement("div");
  backdrop.setAttribute("role", "dialog");
  backdrop.setAttribute("aria-label", "附件在线预览");
  backdrop.style.cssText = "position:fixed;inset:0;height:100dvh;display:flex;flex-direction:column;overflow:hidden;z-index:10000;background:#fff";

  const toolbar = document.createElement("div");
  toolbar.style.cssText = "display:flex;justify-content:flex-end;flex-shrink:0;padding:calc(8px + env(safe-area-inset-top)) max(12px, env(safe-area-inset-right)) 8px max(12px, env(safe-area-inset-left));border-bottom:1px solid #dfe2e7";

  const frame = document.createElement("iframe");
  frame.title = "附件在线预览内容";
  frame.style.cssText = "display:block;width:100%;flex:1;min-height:0;border:0";

  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.textContent = "关闭预览";
  closeButton.style.cssText = "box-sizing:border-box;min-width:44px;min-height:44px;padding:8px 12px;border:1px solid #dfe2e7;border-radius:4px;background:#fff;color:#1f2329;font:inherit;cursor:pointer";

  const cleanupListeners = [];
  let closed = false;
  const target = {
    get closed() {
      return closed;
    },
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
  toolbar.append(closeButton);
  backdrop.append(toolbar, frame);
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
  if (isInlineAttachmentPreviewEnvironment() || window.matchMedia("(max-width: 767px)").matches) {
    return createInlinePreviewTarget();
  }
  return window.open("about:blank", "_blank");
}
