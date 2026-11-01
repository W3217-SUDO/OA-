import { useCallback, useEffect, useRef, useState } from "react";

// 报表页右上角“大屏展示”：把本页内容全屏放大展示，不再跳到经营数据大屏（BUG 500789，思法汇成 11-01）。
// 浏览器不支持全屏（如部分钉钉内核）时，仍按大屏样式铺满窗口。
export function useReportBigScreen() {
  const ref = useRef<HTMLDivElement | null>(null);
  const [active, setActive] = useState(false);

  useEffect(() => {
    const sync = () => {
      if (!document.fullscreenElement && active && ref.current?.dataset.fullscreen === "1") {
        delete ref.current.dataset.fullscreen;
        setActive(false);
      }
    };
    document.addEventListener("fullscreenchange", sync);
    return () => document.removeEventListener("fullscreenchange", sync);
  }, [active]);

  const enter = useCallback(() => {
    setActive(true);
    const element = ref.current;
    if (element?.requestFullscreen) {
      void element.requestFullscreen().then(() => { element.dataset.fullscreen = "1"; }).catch(() => undefined);
    }
  }, []);
  const exit = useCallback(() => {
    setActive(false);
    if (ref.current) delete ref.current.dataset.fullscreen;
    if (document.fullscreenElement) void document.exitFullscreen?.().catch(() => undefined);
  }, []);
  return { ref, active, enter, exit };
}
