import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import { Button, Tooltip } from "antd";
import { CloseOutlined, CompressOutlined, ExpandOutlined, MenuFoldOutlined, PushpinOutlined, RobotOutlined, SelectOutlined } from "@ant-design/icons";

// 501165（tgn 11-03 07:36）：案件智能体停靠在右侧，不遮挡左侧案件信息；默认占页面宽度 2/9，
// 拖左边缘调宽，可放大、收起成右侧小按钮，也可拖出成浮动窗口；每人上次的宽度和位置记在本机。手机仍全屏。
export const DOCK_DEFAULT_RATIO = 2 / 9;
export const DOCK_MIN_WIDTH = 320;
export const DOCK_MAX_RATIO = 0.7;
const TOPBAR = 50;
const MOBILE_QUERY = "(max-width: 767px)";
const BODY_CLASS = "case-agent-docked";

type FloatRect = { x: number; y: number; w: number; h: number };
export type DockLayout = { mode: "docked" | "floating"; ratio: number; float: FloatRect | null };

const storageKey = () => {
  try {
    const user = JSON.parse(localStorage.getItem("user") || "null");
    return `oa.caseAgentDock.v1.${user?.username || "anonymous"}`;
  } catch { return "oa.caseAgentDock.v1.anonymous"; }
};

export function clampRatio(ratio: number, viewport: number) {
  const min = Math.min(DOCK_MIN_WIDTH / Math.max(viewport, 1), DOCK_MAX_RATIO);
  return Math.min(DOCK_MAX_RATIO, Math.max(min, Number.isFinite(ratio) ? ratio : DOCK_DEFAULT_RATIO));
}

export function clampFloat(rect: FloatRect, viewport: { width: number; height: number }): FloatRect {
  const w = Math.min(Math.max(DOCK_MIN_WIDTH, rect.w), viewport.width);
  const h = Math.min(Math.max(320, rect.h), viewport.height - TOPBAR);
  // 标题栏始终留在可见范围内，拖到边上也能拖回来。
  const x = Math.min(Math.max(0, rect.x), Math.max(0, viewport.width - w));
  const y = Math.min(Math.max(TOPBAR, rect.y), Math.max(TOPBAR, viewport.height - 48));
  return { x, y, w, h };
}

export function readDockLayout(): DockLayout {
  try {
    const value = JSON.parse(localStorage.getItem(storageKey()) || "null");
    if (value && (value.mode === "docked" || value.mode === "floating")) {
      const float = value.float && ["x", "y", "w", "h"].every((key) => Number.isFinite(value.float[key])) ? value.float : null;
      return { mode: value.mode === "floating" && float ? "floating" : "docked", ratio: Number(value.ratio) || DOCK_DEFAULT_RATIO, float };
    }
  } catch { /* 本机存储不可用时用默认布局 */ }
  return { mode: "docked", ratio: DOCK_DEFAULT_RATIO, float: null };
}

function saveDockLayout(layout: DockLayout) {
  try { localStorage.setItem(storageKey(), JSON.stringify(layout)); } catch { /* 存不下就不记 */ }
}

function useViewport() {
  const read = () => ({ width: window.innerWidth, height: window.innerHeight, mobile: !!window.matchMedia?.(MOBILE_QUERY).matches });
  const [viewport, setViewport] = useState(read);
  useEffect(() => {
    const onResize = () => setViewport(read());
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return viewport;
}

type Props = { open: boolean; title: ReactNode; onClose: () => void; children: ReactNode };

export function CaseAgentDock({ open, title, onClose, children }: Props) {
  const viewport = useViewport();
  const [layout, setLayout] = useState<DockLayout>(readDockLayout);
  const [collapsed, setCollapsed] = useState(false);
  const [maximized, setMaximized] = useState(false);
  const layoutRef = useRef(layout);
  layoutRef.current = layout;
  const update = useCallback((next: DockLayout, persist = true) => { setLayout(next); if (persist) saveDockLayout(next); }, []);
  useEffect(() => { if (open) { setCollapsed(false); setMaximized(false); } }, [open]);

  const docked = open && !collapsed && !viewport.mobile && layout.mode === "docked";
  const dockWidth = maximized ? viewport.width : Math.round(clampRatio(layout.ratio, viewport.width) * viewport.width);
  // 停靠时左侧页面让出面板宽度，案件信息随之自适应；浮动、收起、关闭时还原。
  useEffect(() => {
    const root = document.body;
    if (docked && !maximized) {
      root.classList.add(BODY_CLASS);
      root.style.setProperty("--case-agent-dock-width", `${dockWidth}px`);
    } else {
      root.classList.remove(BODY_CLASS);
      root.style.removeProperty("--case-agent-dock-width");
    }
  }, [docked, maximized, dockWidth]);
  useEffect(() => () => { document.body.classList.remove(BODY_CLASS); document.body.style.removeProperty("--case-agent-dock-width"); }, []);

  const drag = (event: ReactPointerEvent, onMove: (dx: number, dy: number, moveEvent: PointerEvent) => void, onEnd?: () => void) => {
    if (event.button !== 0) return;
    event.preventDefault();
    const startX = event.clientX, startY = event.clientY;
    const move = (moveEvent: PointerEvent) => onMove(moveEvent.clientX - startX, moveEvent.clientY - startY, moveEvent);
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); onEnd?.(); };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const floatRect = (): FloatRect => clampFloat(layoutRef.current.float || {
    x: viewport.width - dockWidth - 24, y: TOPBAR + 24, w: Math.max(dockWidth, 380), h: Math.round((viewport.height - TOPBAR) * 0.8),
  }, viewport);

  // 停靠时拖左边缘调宽；浮动时拖左右边和右下角调大小。
  const resizeDock = (event: ReactPointerEvent) => {
    const start = dockWidth;
    let latest = layoutRef.current;
    drag(event, (dx) => { latest = { ...layoutRef.current, ratio: clampRatio((start - dx) / viewport.width, viewport.width) }; update(latest, false); }, () => saveDockLayout(latest));
  };
  const resizeFloat = (edge: "left" | "right" | "corner") => (event: ReactPointerEvent) => {
    const start = floatRect();
    let latest = layoutRef.current;
    drag(event, (dx, dy) => {
      const next = edge === "left" ? { ...start, x: start.x + dx, w: start.w - dx } : { ...start, w: start.w + dx, h: edge === "corner" ? start.h + dy : start.h };
      latest = { ...layoutRef.current, float: clampFloat(next, viewport) };
      update(latest, false);
    }, () => saveDockLayout(latest));
  };
  // 拖标题栏：浮动时移动位置；停靠时往外拖超过 12px 就变成浮动窗口跟着鼠标走。
  const moveHeader = (event: ReactPointerEvent) => {
    if ((event.target as HTMLElement).closest("button")) return;
    if (maximized) return;
    const startMode = layoutRef.current.mode;
    const start = startMode === "floating" ? floatRect() : { ...floatRect(), x: viewport.width - dockWidth, y: TOPBAR, w: dockWidth };
    const grabX = event.clientX - start.x, grabY = event.clientY - start.y;
    let detached = startMode === "floating";
    let latest = layoutRef.current;
    drag(event, (dx, dy, moveEvent) => {
      if (!detached && Math.abs(dx) + Math.abs(dy) < 12) return;
      detached = true;
      const rect = clampFloat({ ...start, x: moveEvent.clientX - grabX, y: moveEvent.clientY - grabY, h: startMode === "floating" ? start.h : Math.round((viewport.height - TOPBAR) * 0.8) }, viewport);
      latest = { ...layoutRef.current, mode: "floating", float: rect };
      update(latest, false);
    }, () => { if (detached) saveDockLayout(latest); });
  };

  if (!open) return null;
  if (collapsed) return <button type="button" className="case-agent-dock-tab" aria-label="展开案件智能体" title="展开案件智能体" onClick={() => setCollapsed(false)}>
    <RobotOutlined /><span>案件智能体</span>
  </button>;

  const mobile = viewport.mobile;
  const floating = !mobile && !maximized && layout.mode === "floating";
  const rect = floating ? floatRect() : null;
  const style = mobile ? undefined
    : maximized ? { top: TOPBAR, right: 0, bottom: 0, left: 0 }
    : rect ? { top: rect.y, left: rect.x, width: rect.w, height: rect.h }
    : { top: TOPBAR, right: 0, bottom: 0, width: dockWidth };
  const className = `case-agent-dock${mobile ? " is-mobile" : maximized ? " is-maximized" : floating ? " is-floating" : " is-docked"}`;
  return <section className={className} style={style} role="complementary" aria-label="案件智能体">
    <header className="case-agent-dock-header" onPointerDown={mobile ? undefined : moveHeader}>
      <span className="case-agent-dock-title">{title}</span>
      <span className="case-agent-dock-actions">
        {!mobile && <>
          <Tooltip title={layout.mode === "floating" ? "停靠到右侧" : "变成浮动窗口"}><Button type="text" size="small" icon={layout.mode === "floating" ? <PushpinOutlined /> : <SelectOutlined />} aria-label={layout.mode === "floating" ? "停靠到右侧" : "变成浮动窗口"} disabled={maximized}
            onClick={() => update(layout.mode === "floating" ? { ...layout, mode: "docked" } : { ...layout, mode: "floating", float: floatRect() })} /></Tooltip>
          <Tooltip title={maximized ? "还原" : "放大"}><Button type="text" size="small" icon={maximized ? <CompressOutlined /> : <ExpandOutlined />} aria-label={maximized ? "还原" : "放大"} onClick={() => setMaximized(!maximized)} /></Tooltip>
          <Tooltip title="收起到右侧"><Button type="text" size="small" icon={<MenuFoldOutlined />} aria-label="收起" onClick={() => { setMaximized(false); setCollapsed(true); }} /></Tooltip>
        </>}
        <Tooltip title="关闭"><Button type="text" size="small" icon={<CloseOutlined />} aria-label="关闭案件智能体" onClick={onClose} /></Tooltip>
      </span>
    </header>
    <div className="case-agent-dock-body">{children}</div>
    {!mobile && !maximized && !floating && <div className="case-agent-dock-resize is-left" role="separator" aria-label="拖动调整智能体宽度" onPointerDown={resizeDock} />}
    {floating && <>
      <div className="case-agent-dock-resize is-left" role="separator" aria-label="拖动调整智能体宽度" onPointerDown={resizeFloat("left")} />
      <div className="case-agent-dock-resize is-right" role="separator" aria-label="拖动调整智能体宽度" onPointerDown={resizeFloat("right")} />
      <div className="case-agent-dock-resize is-corner" role="separator" aria-label="拖动调整智能体大小" onPointerDown={resizeFloat("corner")} />
    </>}
  </section>;
}
