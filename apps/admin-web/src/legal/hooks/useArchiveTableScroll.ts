import { useLayoutEffect, useRef, useState } from "react";

export function useArchiveTableScroll(enabled: boolean, route: string) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState({ body: 1, minimum: 1 });

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!enabled || !container) return;
    const table = container.querySelector<HTMLElement>(".ant-table-wrapper");
    const body = container.querySelector<HTMLElement>(".ant-table-body");
    if (!table || !body) return;

    // 表格非表体部分包含表头、分页及其间距，按实际尺寸预留，不依赖视口扣减常量。
    const measure = () => {
      const reservedHeight = table.getBoundingClientRect().height - body.getBoundingClientRect().height;
      const nextHeight = Math.max(1, Math.floor(container.clientHeight - reservedHeight));
      const minimumHeight = Math.ceil(reservedHeight) + 1;
      setHeight(current => current.body === nextHeight && current.minimum === minimumHeight
        ? current
        : { body: nextHeight, minimum: minimumHeight });
    };
    let frame: number | undefined;
    const observer = new ResizeObserver(() => {
      if (frame !== undefined) cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        frame = undefined;
        measure();
      });
    });
    measure();
    observer.observe(container);
    observer.observe(table);
    observer.observe(body);
    return () => {
      observer.disconnect();
      if (frame !== undefined) cancelAnimationFrame(frame);
    };
  }, [enabled, route]);

  return { containerRef, scrollY: enabled ? height.body : undefined, minHeight: enabled ? height.minimum : undefined };
}
