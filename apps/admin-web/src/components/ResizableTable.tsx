import { useEffect, useMemo, useRef, useState } from "react";
import { Table as AntTable } from "antd";
import type { TableColumnsType, TableProps } from "antd";
import "./resizable-table.css";

const MIN_COLUMN_WIDTH = 48;
const RESIZE_EDGE_WIDTH = 9;

type ResizeSession = { stop: () => void };

function columnSignature<RecordType extends object>(columns: TableColumnsType<RecordType>): string {
  const parts: string[] = [];
  const visit = (items: TableColumnsType<RecordType>, parentKey = "") => {
    items.forEach((column, index) => {
      const path = `${parentKey}${index}`;
      const field = "dataIndex" in column ? column.dataIndex : undefined;
      const title = typeof column.title === "string" ? column.title : "";
      parts.push(`${path}:${String(column.key ?? (Array.isArray(field) ? field.join(".") : field) ?? title)}`);
      if ("children" in column && column.children?.length) visit(column.children, `${path}.`);
    });
  };
  visit(columns);
  return parts.join("|");
}

function storedWidths(key: string): Record<string, number> {
  const saved = sessionStorage.getItem(key);
  if (!saved) return {};
  const value: unknown = JSON.parse(saved);
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(Object.entries(value).filter(([, width]) => typeof width === "number" && Number.isFinite(width) && width >= MIN_COLUMN_WIDTH && width <= 2000));
}

function ResizableTable<RecordType extends object>({ columns, className, ...props }: TableProps<RecordType>) {
  const storageKey = useMemo(() => {
    const route = new URLSearchParams(window.location.search).get("page") || window.location.pathname;
    return `sunhold:table-widths:${route}:${className || ""}:${columnSignature(columns || [])}`;
  }, [className, columns]);
  const [widths, setWidths] = useState<Record<string, number>>(() => storedWidths(storageKey));
  const widthsRef = useRef(widths);
  const previousStorageKey = useRef(storageKey);
  const activeResize = useRef<ResizeSession | null>(null);
  const ignoredClick = useRef<string | null>(null);

  useEffect(() => () => activeResize.current?.stop(), []);
  useEffect(() => {
    if (previousStorageKey.current === storageKey) return;
    previousStorageKey.current = storageKey;
    const nextWidths = storedWidths(storageKey);
    widthsRef.current = nextWidths;
    setWidths(nextWidths);
  }, [storageKey]);

  const resizedColumns = useMemo((): TableColumnsType<RecordType> | undefined => {
    if (!columns) return undefined;
    const decorate = (items: TableColumnsType<RecordType>, parentKey = ""): TableColumnsType<RecordType> =>
      items.map((column, index) => {
        if (column === AntTable.SELECTION_COLUMN || column === AntTable.EXPAND_COLUMN) return column;
        const columnKey = `${parentKey}${index}`;
        if ("children" in column && column.children?.length) {
          return { ...column, children: decorate(column.children, `${columnKey}.`) };
        }
        const originalHeaderCell = column.onHeaderCell;
        const adjustedWidth = widths[columnKey];
        return {
          ...column,
          ...(adjustedWidth === undefined ? {} : { width: adjustedWidth, ellipsis: true }),
          onHeaderCell: (headerColumn) => {
            const originalProps = originalHeaderCell?.(headerColumn) || {};
            const originalPointerDown = originalProps.onPointerDown;
            const originalClickCapture = originalProps.onClickCapture;
            return {
              ...originalProps,
              className: [originalProps.className, "oa-resizable-header"].filter(Boolean).join(" "),
              onPointerDown: (event: React.PointerEvent<HTMLTableCellElement>) => {
                originalPointerDown?.(event);
                if (event.defaultPrevented || (event.pointerType === "mouse" && event.button !== 0)) return;
                const rightEdge = event.currentTarget.getBoundingClientRect().right;
                if (rightEdge - event.clientX > RESIZE_EDGE_WIDTH || rightEdge - event.clientX < 0) return;
                event.preventDefault();
                event.stopPropagation();
                activeResize.current?.stop();
                const startWidth = event.currentTarget.getBoundingClientRect().width;
                const startX = event.clientX;
                const previousCursor = document.body.style.cursor;
                const previousSelection = document.body.style.userSelect;
                document.body.style.cursor = "col-resize";
                document.body.style.userSelect = "none";
                ignoredClick.current = columnKey;
                const onMove = (moveEvent: PointerEvent) => {
                  const nextWidths = {
                    ...widthsRef.current,
                    [columnKey]: Math.max(MIN_COLUMN_WIDTH, Math.round(startWidth + moveEvent.clientX - startX)),
                  };
                  widthsRef.current = nextWidths;
                  setWidths(nextWidths);
                };
                const stop = () => {
                  window.removeEventListener("pointermove", onMove);
                  window.removeEventListener("pointerup", stop);
                  window.removeEventListener("pointercancel", stop);
                  document.body.style.cursor = previousCursor;
                  document.body.style.userSelect = previousSelection;
                  sessionStorage.setItem(storageKey, JSON.stringify(widthsRef.current));
                  activeResize.current = null;
                  window.setTimeout(() => { if (ignoredClick.current === columnKey) ignoredClick.current = null; }, 400);
                };
                activeResize.current = { stop };
                window.addEventListener("pointermove", onMove);
                window.addEventListener("pointerup", stop);
                window.addEventListener("pointercancel", stop);
              },
              onClickCapture: (event: React.MouseEvent<HTMLTableCellElement>) => {
                originalClickCapture?.(event);
                if (ignoredClick.current === columnKey) {
                  event.preventDefault();
                  event.stopPropagation();
                  ignoredClick.current = null;
                }
              },
            };
          },
        };
      });
    return decorate(columns);
  }, [columns, widths]);

  return <AntTable<RecordType> {...props} className={[className, "oa-resizable-table"].filter(Boolean).join(" ")} columns={resizedColumns} />;
}

const Table = Object.assign(ResizableTable, {
  Column: AntTable.Column,
  ColumnGroup: AntTable.ColumnGroup,
  Summary: AntTable.Summary,
  SELECTION_COLUMN: AntTable.SELECTION_COLUMN,
  EXPAND_COLUMN: AntTable.EXPAND_COLUMN,
}) as typeof AntTable;

export default Table;
