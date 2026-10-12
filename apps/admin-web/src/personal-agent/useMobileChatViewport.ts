import { useLayoutEffect, useRef } from "react";

export function useMobileChatViewport(enabled: boolean) {
  const rootRef = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    const root = rootRef.current;
    const viewport = window.visualViewport;
    if (!enabled || !root || !viewport) return;

    const mobileQuery = window.matchMedia("(max-width: 991px)");
    let listening = false;
    let frame: number | null = null;

    const updateViewport = () => {
      frame = null;
      // 键盘改变的是可见视口，仅在当前聊天根容器同步高度和顶边偏移。
      root.style.setProperty("--mobile-chat-viewport-height", `${viewport.height}px`);
      root.style.setProperty("--mobile-chat-viewport-top", `${viewport.offsetTop}px`);
    };
    const scheduleUpdate = () => {
      if (frame === null) frame = window.requestAnimationFrame(updateViewport);
    };
    const releaseViewport = () => {
      if (listening) {
        viewport.removeEventListener("resize", scheduleUpdate);
        viewport.removeEventListener("scroll", scheduleUpdate);
        listening = false;
      }
      if (frame !== null) {
        window.cancelAnimationFrame(frame);
        frame = null;
      }
      root.style.removeProperty("--mobile-chat-viewport-height");
      root.style.removeProperty("--mobile-chat-viewport-top");
    };
    const synchronizeMobile = () => {
      if (!mobileQuery.matches) {
        releaseViewport();
        return;
      }
      if (!listening) {
        viewport.addEventListener("resize", scheduleUpdate);
        viewport.addEventListener("scroll", scheduleUpdate);
        listening = true;
      }
      if (frame !== null) window.cancelAnimationFrame(frame);
      updateViewport();
    };

    mobileQuery.addEventListener("change", synchronizeMobile);
    synchronizeMobile();
    return () => {
      mobileQuery.removeEventListener("change", synchronizeMobile);
      releaseViewport();
    };
  }, [enabled]);

  return rootRef;
}
