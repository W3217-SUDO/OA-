import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Button, Tooltip } from "antd";
import { CloseOutlined, CompressOutlined, ExpandOutlined, MenuFoldOutlined, RobotOutlined } from "@ant-design/icons";

// 501165（tgn 11-03）：案件智能体是浮在案件页上面的窗口，遮挡没关系，不压缩案件页。
// 打开时在右下角，宽 2/9、高约可视区 70%；可拖动、调大小、放大、收起；每人上次的大小和位置记在本机。
// 窗口挂到 body 下用 fixed 定位跟视口走，拖动和窗口缩放时始终夹在可视区内，不会掉到页面底下（tgn 08:06）。手机全屏。
export const WINDOW_DEFAULT_WIDTH = 2 / 9;
export const WINDOW_DEFAULT_HEIGHT = 0.7;
export const WINDOW_MIN_WIDTH = 320;
export const WINDOW_MIN_HEIGHT = 320;
const TOPBAR = 50;
const MARGIN = 16;
const MOBILE_QUERY = "(max-width: 767px)";

export type WindowRect = { x: number; y: number; w: number; h: number };
type Viewport = { width: number; height: number };

const storageKey = () => {
  try {
    const user = JSON.parse(localStorage.getItem("user") || "null");
    return `oa.caseAgentWindow.v3.${user?.username || "anonymous"}`;
  } catch { return "oa.caseAgentWindow.v3.anonymous"; }
};

export function defaultRect(viewport: Viewport): WindowRect {
  const w = Math.min(Math.max(WINDOW_MIN_WIDTH, Math.round(viewport.width * WINDOW_DEFAULT_WIDTH)), viewport.width - MARGIN * 2);
  const h = Math.min(Math.max(WINDOW_MIN_HEIGHT, Math.round((viewport.height - TOPBAR) * WINDOW_DEFAULT_HEIGHT)), viewport.height - TOPBAR - MARGIN * 2);
  return { x: viewport.width - w - MARGIN, y: viewport.height - h - MARGIN, w, h };
}

/** 整个窗口留在可视区内：先限制大小不超过可视区，再把位置夹到可视区里。 */
export function clampRect(rect: WindowRect, viewport: Viewport): WindowRect {
  const maxW = Math.max(200, viewport.width);
  const maxH = Math.max(200, viewport.height - TOPBAR);
  const w = Math.min(Math.max(Math.min(WINDOW_MIN_WIDTH, maxW), rect.w), maxW);
  const h = Math.min(Math.max(Math.min(WINDOW_MIN_HEIGHT, maxH), rect.h), maxH);
  const x = Math.min(Math.max(0, rect.x), viewport.width - w);
  const y = Math.min(Math.max(TOPBAR, rect.y), viewport.height - h);
  return { x, y, w, h };
}

/** 记住的位置只有整个窗口都在当前可视区内才沿用，否则回到右下角默认位置。 */
export function visibleRect(rect: WindowRect | null, viewport: Viewport): WindowRect {
  if (!rect || !["x", "y", "w", "h"].every((key) => Number.isFinite(rect[key as keyof WindowRect]))) return defaultRect(viewport);
  const clamped = clampRect(rect, viewport);
  return clamped.x === rect.x && clamped.y === rect.y && clamped.w === rect.w && clamped.h === rect.h ? rect : defaultRect(viewport);
}

function readRect(): WindowRect | null {
  try { return JSON.parse(localStorage.getItem(storageKey()) || "null"); } catch { return null; }
}

function saveRect(rect: WindowRect) {
  try { localStorage.setItem(storageKey(), JSON.stringify(rect)); } catch { /* 存不下就不记 */ }
}

function readViewport() {
  return { width: window.innerWidth, height: window.innerHeight, mobile: !!window.matchMedia?.(MOBILE_QUERY).matches };
}

type Props = { open: boolean; title: ReactNode; onClose: () => void; children: ReactNode;
  /** 每次点“案件智能体”加一：窗口已打开也重新显示并拉回可视区。 */
  revealKey?: number };

export function CaseAgentDock({ open, title, onClose, children, revealKey = 0 }: Props) {
  const [viewport, setViewport] = useState(readViewport);
  const [rect, setRect] = useState<WindowRect>(() => visibleRect(readRect(), viewport));
  const [collapsed, setCollapsed] = useState(false);
  const [maximized, setMaximized] = useState(false);
  const rectRef = useRef(rect);
  rectRef.current = rect;

  // 打开或再次点“案件智能体”：展开、取消放大，位置不在可视区就回到右下角。
  useEffect(() => {
    if (!open) return;
    const current = readViewport();
    setViewport(current);
    setCollapsed(false);
    setMaximized(false);
    // 默认位置按此刻的可视区算（组件可能在窗口还小时就已挂载）；拖动松手时已记下位置。
    setRect(visibleRect(readRect(), current));
  }, [open, revealKey]);
  // 浏览器窗口变小时把智能体一起收进可视区。
  useEffect(() => {
    const onResize = () => { const next = readViewport(); setViewport(next); setRect((current) => clampRect(current, next)); };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const drag = useCallback((event: ReactPointerEvent, compute: (start: WindowRect, dx: number, dy: number) => WindowRect) => {
    if (event.button !== 0) return;
    event.preventDefault();
    const startX = event.clientX, startY = event.clientY, start = rectRef.current;
    let latest = start;
    const move = (moveEvent: PointerEvent) => {
      latest = clampRect(compute(start, moveEvent.clientX - startX, moveEvent.clientY - startY), readViewport());
      setRect(latest);
    };
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); window.removeEventListener("pointercancel", up); saveRect(latest); };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
  }, []);

  const moveWindow = (event: ReactPointerEvent) => {
    if (maximized || (event.target as HTMLElement).closest?.("button")) return;
    drag(event, (start, dx, dy) => ({ ...start, x: start.x + dx, y: start.y + dy }));
  };
  const resize = (edge: "left" | "right" | "top" | "corner") => (event: ReactPointerEvent) => drag(event, (start, dx, dy) => {
    if (edge === "left") return { ...start, x: start.x + dx, w: start.w - dx };
    if (edge === "top") return { ...start, y: start.y + dy, h: start.h - dy };
    if (edge === "right") return { ...start, w: start.w + dx };
    return { ...start, w: start.w + dx, h: start.h + dy };
  });

  if (!open || typeof document === "undefined") return null;
  if (collapsed) return createPortal(<button type="button" className="case-agent-dock-tab" aria-label="展开案件智能体" title="展开案件智能体" onClick={() => setCollapsed(false)}>
    <RobotOutlined /><span>案件智能体</span>
  </button>, document.body);

  const mobile = viewport.mobile;
  const style = mobile ? undefined
    : maximized ? { top: TOPBAR, right: 0, bottom: 0, left: 0 }
    : { top: rect.y, left: rect.x, width: rect.w, height: rect.h };
  const className = `case-agent-dock${mobile ? " is-mobile" : maximized ? " is-maximized" : " is-floating"}`;
  return createPortal(<section className={className} style={style} role="dialog" aria-modal={false} aria-label="案件智能体">
    <header className="case-agent-dock-header" onPointerDown={mobile ? undefined : moveWindow}>
      <span className="case-agent-dock-title">{title}</span>
      <span className="case-agent-dock-actions">
        {!mobile && <>
          <Tooltip title={maximized ? "还原" : "放大"}><Button type="text" size="small" icon={maximized ? <CompressOutlined /> : <ExpandOutlined />} aria-label={maximized ? "还原" : "放大"} onClick={() => setMaximized(!maximized)} /></Tooltip>
          <Tooltip title="收起到右侧"><Button type="text" size="small" icon={<MenuFoldOutlined />} aria-label="收起" onClick={() => { setMaximized(false); setCollapsed(true); }} /></Tooltip>
        </>}
        <Tooltip title="关闭"><Button type="text" size="small" icon={<CloseOutlined />} aria-label="关闭案件智能体" onClick={onClose} /></Tooltip>
      </span>
    </header>
    <div className="case-agent-dock-body">{children}</div>
    {!mobile && !maximized && <>
      <div className="case-agent-dock-resize is-left" role="separator" aria-label="拖动调整智能体宽度" onPointerDown={resize("left")} />
      <div className="case-agent-dock-resize is-right" role="separator" aria-label="拖动调整智能体右边" onPointerDown={resize("right")} />
      <div className="case-agent-dock-resize is-top" role="separator" aria-label="拖动调整智能体高度" onPointerDown={resize("top")} />
      <div className="case-agent-dock-resize is-corner" role="separator" aria-label="拖动调整智能体大小" onPointerDown={resize("corner")} />
    </>}
  </section>, document.body);
}
