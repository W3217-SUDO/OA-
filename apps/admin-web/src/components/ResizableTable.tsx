import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Table as AntTable } from "antd";
import type { TableColumnsType, TableProps } from "antd";
import "./resizable-table.css";

const MIN_COLUMN_WIDTH = 48;
const RESIZE_EDGE_WIDTH = 9;
// 列宽自适应：按表头和实际数据估算每列需要的宽度，能在一屏内放下就不出现横向滚动，放不下才保留原列宽横向滚动。
const FIT_MIN_COLUMN_WIDTH = 40;
// 放不下时的紧凑模式：单元格左右内边距各 4px。
const FIT_DENSE_PADDING = 10;
const FIT_CELL_PADDING = 22;
const FIT_SAMPLE_ROWS = 60;

type ResizeSession = { stop: () => void };
// 宽表在一屏放不下时，可把相关列叠放到同一个单元格（如“合同号/合同名称”、官费的四个金额），数据一项不少；屏幕够宽时仍分列显示。
export type FitStackGroup = { title: ReactNode; keys: string[]; labels?: string[] };
// 表格自带合计行（summary 或自定义表头/表体行）时，这些行按原列位置排单元格；只有声明已适配叠放的表才允许叠放，避免合计错位。
export type FitStackAware = { summary?: boolean; body?: boolean; header?: boolean };
export type FitStackSpec = { keys: string[]; labels?: string[] }[];
export type FitStackState = { stacked: boolean; groups: FitStackSpec };
type ResizableTableProps<RecordType extends object> = Omit<TableProps<RecordType>, "summary"> & {
  resizable?: boolean;
  fitStack?: FitStackGroup[];
  fitStackAware?: FitStackAware;
  summary?: (data: readonly RecordType[], fit?: FitStackState) => ReactNode;
};

// 列的标识：优先 key，其次 dataIndex，都没有时用文字表头。
function columnId(column: object): string {
  const record = column as { key?: unknown; dataIndex?: unknown; title?: unknown };
  if (record.key !== undefined && record.key !== null) return String(record.key);
  if (record.dataIndex !== undefined && record.dataIndex !== null) return Array.isArray(record.dataIndex) ? record.dataIndex.join(".") : String(record.dataIndex);
  return typeof record.title === "string" ? record.title : "";
}

function renderMember<RecordType extends object>(column: TableColumnsType<RecordType>[number], record: RecordType, index: number): ReactNode {
  const dataIndex = "dataIndex" in column ? column.dataIndex : undefined;
  const path = dataIndex === undefined ? [] : Array.isArray(dataIndex) ? dataIndex : [dataIndex];
  let value: unknown = record;
  for (const key of path) value = value && typeof value === "object" ? (value as Record<string, unknown>)[String(key)] : undefined;
  if (!path.length) value = undefined;
  const render = "render" in column ? column.render : undefined;
  const output = render ? render(value, record, index) : value;
  if (output && typeof output === "object" && "children" in (output as object) && "props" in (output as object) && !("$$typeof" in (output as object))) {
    return (output as { children: ReactNode }).children;
  }
  return (output ?? "") as ReactNode;
}

// 把分组里的列合并成一列：每个原列占一行，可带短标签；排序沿用组内第一个可排序的列。
function stackColumns<RecordType extends object>(columns: TableColumnsType<RecordType>, leaves: FitLeaf[], groups: FitStackGroup[]) {
  const stackedColumns: TableColumnsType<RecordType> = [];
  const stackedLeaves: FitLeaf[] = [];
  // 每个实际渲染的列对应原来的哪个（或哪几个）列，用来在叠放后继续按真实单元格测量。
  const layout: (number | number[])[] = [];
  let leafIndex = 0;
  const memberIds = new Set(groups.flatMap((group) => group.keys));
  const leafOf = new Map<string, FitLeaf>();
  const leafIndexOf = new Map<string, number>();
  const columnOf = new Map<string, TableColumnsType<RecordType>[number]>();
  columns.forEach((column) => {
    const count = "children" in column && column.children?.length ? measureLeafCount(column.children) : 1;
    if (count === 1 && memberIds.has(columnId(column))) {
      leafOf.set(columnId(column), leaves[leafIndex]);
      leafIndexOf.set(columnId(column), leafIndex);
      columnOf.set(columnId(column), column);
    }
    leafIndex += count;
  });
  leafIndex = 0;
  columns.forEach((column) => {
    const count = "children" in column && column.children?.length ? measureLeafCount(column.children) : 1;
    const id = columnId(column);
    const group = count === 1 ? groups.find((item) => item.keys.includes(id)) : undefined;
    const complete = group && group.keys.every((key) => columnOf.has(key));
    if (group && complete) {
      if (group.keys[0] === id) {
        const members = group.keys.map((key) => columnOf.get(key)!);
        const memberLeaves = group.keys.map((key) => leafOf.get(key)!);
        const labelWidth = group.labels ? Math.max(...group.labels.map((label) => textWidth(label))) + 12 : 0;
        const declared = Math.max(...memberLeaves.map((leaf) => leaf.declared)) + labelWidth;
        const sortable = members.find((member) => member.sorter);
        stackedColumns.push({
          ...(sortable ? { sorter: sortable.sorter, sortOrder: sortable.sortOrder, dataIndex: "dataIndex" in sortable ? sortable.dataIndex : undefined } : {}),
          key: sortable ? sortable.key ?? columnId(sortable) : `stack:${group.keys.join("+")}`,
          title: group.title,
          width: declared,
          className: "oa-stack-column",
          render: (_value: unknown, record: RecordType, index: number) => (
            <div className={`oa-stack-cell${group.labels ? " has-labels" : ""}`}>
              {members.map((member, memberIndex) => (
                <div className="oa-stack-line" key={columnId(member)}>
                  {group.labels && <span className="oa-stack-label">{group.labels[memberIndex]}</span>}
                  <span className={`oa-stack-value${memberLeaves[memberIndex]?.numeric ? " is-number" : ""}`}>{renderMember(member, record, index)}</span>
                </div>
              ))}
            </div>
          ),
        } as TableColumnsType<RecordType>[number]);
        layout.push(group.keys.map((key) => leafIndexOf.get(key)!));
        stackedLeaves.push({
          declared,
          min: Math.max(...memberLeaves.map((leaf) => leaf.min)) + labelWidth,
          want: Math.max(...memberLeaves.map((leaf) => leaf.want)) + labelWidth,
          locked: false,
        });
      }
    } else {
      stackedColumns.push(column);
      stackedLeaves.push(...leaves.slice(leafIndex, leafIndex + count));
      for (let offset = 0; offset < count; offset += 1) layout.push(leafIndex + offset);
    }
    leafIndex += count;
  });
  return { columns: stackedColumns, leaves: stackedLeaves, layout };
}

function measureLeafCount<RecordType extends object>(columns: TableColumnsType<RecordType>): number {
  return columns.reduce((sum, column) => sum + ("children" in column && column.children?.length ? measureLeafCount(column.children) : 1), 0);
}

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

type TableHandle = { nativeElement?: HTMLElement | null };

function textWidth(text: string) {
  let width = 0;
  for (const char of text) width += /[\u2e80-\uffff]/.test(char) ? 13 : 7.4;
  return width;
}

function cellText(record: unknown, dataIndex: unknown): string {
  if (dataIndex === undefined || dataIndex === null || !record || typeof record !== "object") return "";
  const path = Array.isArray(dataIndex) ? dataIndex : [dataIndex];
  let value: unknown = record;
  for (const key of path) value = value && typeof value === "object" ? (value as Record<string, unknown>)[String(key)] : undefined;
  if (value === null || value === undefined) return "";
  return typeof value === "object" ? "" : String(value);
}

function percentile(values: number[], ratio: number) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * ratio))];
}

type FitLeaf = { declared: number; min: number; want: number; locked: boolean; numeric?: boolean };
// totals 是合计行里金额等不能拆的内容的最大宽度，合计只有一两行，必须整段放下。
type RenderedStats = { typical: number[]; wide: number[]; numeric: boolean[]; solid: number[]; padding: number; header: number[]; totals: number[] };

// 金额、日期、编号这类内容不能被省略。
const UNBREAKABLE_TEXT = /^[¥$￥+\-\d\s,.:/%()（）A-Za-z_-]+$/;
// 只有日期和时间之间是空格时浏览器才能在那里换行；“T”连写的时间戳不能拆，按整段宽度预留。
const DATE_TIME_TEXT = /^(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}) (\d{1,2}:\d{1,2}(?::\d{1,2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)$/;

// “T”连写的时间戳（如 2025-11-13T15:10:30.427）可以分两行完整显示，按一半宽度预留。
const ISO_TIMESTAMP_TEXT = /^\d{4}-\d{2}-\d{2}T\d{1,2}:\d{2}/;
// 24 位以上字母数字混排的系统编号（哈希、UUID 一类）同样允许分两行；金额、日期、20 位发票号仍整行显示。
const LONG_CODE_TEXT = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_-]{24,}$/;
const splitsInTwo = (text: string) => ISO_TIMESTAMP_TEXT.test(text) || LONG_CODE_TEXT.test(text);

function unbreakableWidth(text: string, measure: (value: string) => number = textWidth) {
  if (splitsInTwo(text)) return Math.ceil(measure(text) / 2) + 2;
  const dateTime = DATE_TIME_TEXT.exec(text);
  return dateTime ? Math.max(measure(dateTime[1]), measure(dateTime[2])) : measure(text);
}

// 按单元格实际字体精确量字宽；拿不到画布时退回估算。
function fontMeasurer(font: string): (value: string) => number {
  try {
    const context = document.createElement("canvas").getContext("2d");
    if (!context) return textWidth;
    context.font = font;
    return (value: string) => context.measureText(value).width;
  } catch {
    return textWidth;
  }
}

// 读取已渲染单元格的文字宽度（含自定义渲染后的日期、人名等），按列统计中位数和九成分位。
function readRenderedStats(element: HTMLElement | null | undefined, leafCount: number, layout?: (number | number[])[]): RenderedStats | null {
  if (!element || !leafCount) return null;
  const columnMap = layout ?? Array.from({ length: leafCount }, (_, index) => index);
  const rows = [...element.querySelectorAll<HTMLTableRowElement>(".ant-table-tbody > tr.ant-table-row")].slice(0, FIT_SAMPLE_ROWS);
  // 合计行可能写在表体、表头（自定义表头里的合计）或表尾（summary）里，合计金额通常最长。
  const totalRows = [...new Set(element.querySelectorAll<HTMLTableRowElement>(".ant-table-tbody > tr, .ant-table-thead > tr, tfoot > tr"))]
    .filter((row) => !row.classList.contains("ant-table-row") && !row.classList.contains("ant-table-measure-row") && !row.classList.contains("ant-table-placeholder") && !row.classList.contains("ant-table-expanded-row") && row.querySelector(":scope > td"));
  const headerRow = [...element.querySelectorAll<HTMLTableRowElement>(".ant-table-thead > tr")].filter((row) => row.querySelector(":scope > th")).pop();
  const headerCells = headerRow ? [...headerRow.children].filter((cell) => cell.tagName === "TH" && !cell.classList.contains("ant-table-cell-scrollbar")) : [];
  const headerOffset = headerCells.length - columnMap.length;
  const header: number[] = Array.from({ length: leafCount }, () => 0);
  columnMap.forEach((target, index) => {
    const cell = headerOffset >= 0 ? headerCells[index + headerOffset] : undefined;
    if (cell && typeof target === "number") header[target] = Math.round(cell.getBoundingClientRect().width);
  });
  if (!rows.length) return { typical: [], wide: [], numeric: [], solid: [], padding: FIT_CELL_PADDING, header, totals: [] };
  const sampleCell = rows[0].querySelector<HTMLElement>("td");
  const cellStyle = sampleCell ? getComputedStyle(sampleCell) : null;
  const padding = cellStyle ? Math.ceil(parseFloat(cellStyle.paddingLeft) + parseFloat(cellStyle.paddingRight)) + 2 : FIT_CELL_PADDING;
  // 计算样式里的 font 简写有时为空，按分项拼出完整字体再量。
  const font = cellStyle ? `${cellStyle.fontStyle} ${cellStyle.fontWeight} ${cellStyle.fontSize} ${cellStyle.fontFamily}` : "";
  // 表格数字用等宽数字排版，画布按比例数字量会偏窄；数字越多余量越大（最多约 16%）。
  const baseMeasure = cellStyle?.fontSize ? fontMeasurer(font) : textWidth;
  const measure = (value: string) => {
    const digits = value.replace(/\D/g, "").length;
    const share = value.length ? digits / value.length : 0;
    return baseMeasure(value) * (1.04 + 0.12 * share) + 2;
  };
  const perColumn: number[][] = Array.from({ length: leafCount }, () => []);
  const unbreakable: number[] = Array.from({ length: leafCount }, () => 0);
  const solid: number[][] = Array.from({ length: leafCount }, () => []);
  const filled: number[] = Array.from({ length: leafCount }, () => 0);
  const totals: number[] = Array.from({ length: leafCount }, () => 0);
  // 链接按钮、标签自带左右内边距，要算进内容宽度。
  const chipExtra = (element: HTMLElement) => {
    const chip = element.querySelector<HTMLElement>(".ant-btn, .ant-tag");
    const chipStyle = chip ? getComputedStyle(chip) : null;
    return chipStyle ? parseFloat(chipStyle.paddingLeft) + parseFloat(chipStyle.paddingRight) + parseFloat(chipStyle.borderLeftWidth) + parseFloat(chipStyle.borderRightWidth) : 0;
  };
  const record = (index: number, element: HTMLElement, text: string) => {
    if (!text) return;
    const extra = chipExtra(element);
    perColumn[index].push(Math.ceil(Math.max(...text.split("\n").map(measure)) + extra));
    filled[index] += 1;
    if (UNBREAKABLE_TEXT.test(text)) {
      // 时间戳可折行，不算“不能拆”的数字；但仍按半宽预留，保证最多两行。
      if (!splitsInTwo(text)) unbreakable[index] += 1;
      solid[index].push(Math.ceil(unbreakableWidth(text, measure) + extra));
    }
  };
  const recordTotal = (index: number, element: HTMLElement, text: string) => {
    if (text && UNBREAKABLE_TEXT.test(text)) totals[index] = Math.max(totals[index], Math.ceil(unbreakableWidth(text, measure) + chipExtra(element)));
  };
  // 按单元格实际占的列位置（含 colSpan）对应到原来的列；跨多列的单元格（如“合计”字样）不参与。
  const visitRow = (row: HTMLTableRowElement, take: typeof record) => {
    const cells = [...row.children].filter((cell) => cell.tagName === "TD") as HTMLTableCellElement[];
    const span = cells.reduce((sum, cell) => sum + Math.max(1, cell.colSpan || 1), 0);
    const offset = span - columnMap.length;
    if (offset < 0) return;
    let position = 0;
    cells.forEach((cell) => {
      const index = position - offset;
      position += Math.max(1, cell.colSpan || 1);
      if (cell.colSpan > 1 || index < 0 || index >= columnMap.length) return;
      const target = columnMap[index];
      if (typeof target === "number") {
        take(target, cell, cell.innerText?.trim() || "");
        return;
      }
      const values = [...cell.querySelectorAll<HTMLElement>(".oa-stack-line > .oa-stack-value")];
      target.forEach((leaf, memberIndex) => {
        const value = values[memberIndex];
        if (value) take(leaf, value, value.innerText?.trim() || "");
      });
    });
  };
  rows.forEach((row) => visitRow(row, record));
  totalRows.forEach((row) => visitRow(row, recordTotal));
  return {
    typical: perColumn.map((widths) => Math.round(percentile(widths, 0.5))),
    wide: perColumn.map((widths) => Math.round(percentile(widths, 0.9))),
    numeric: unbreakable.map((count, index) => filled[index] > 0 && count / filled[index] >= 0.8),
    solid: solid.map((widths) => Math.round(percentile(widths, 0.9))),
    padding,
    header,
    totals,
  };
}

function pixelWidth(width: unknown): number {
  if (typeof width === "number") return width;
  if (typeof width === "string" && /^\d+(\.\d+)?(px)?$/.test(width.trim())) return parseFloat(width);
  return 0;
}

function measureLeaves<RecordType extends object>(columns: TableColumnsType<RecordType>, rows: readonly RecordType[], rendered: RenderedStats | null, padOverride?: number): FitLeaf[] {
  const leaves: FitLeaf[] = [];
  const sample = rows.slice(0, FIT_SAMPLE_ROWS);
  let leafIndex = -1;
  const pad = padOverride ?? rendered?.padding ?? FIT_CELL_PADDING;
  const visit = (items: TableColumnsType<RecordType>) => items.forEach((column) => {
    if ("children" in column && column.children?.length) {
      visit(column.children);
      return;
    }
    leafIndex += 1;
    const dataIndex = "dataIndex" in column ? column.dataIndex : undefined;
    const title = typeof column.title === "string" ? column.title.trim() : "";
    const hasRichTitle = Boolean(column.title) && typeof column.title !== "string";
    const isAction = title.includes("操作");
    // 写了像素宽度的按声明宽度；没写的（由样式表或表格自动分配）按实际渲染宽度，读不到时按表头估算。
    const headerEstimate = Math.max(80, Math.ceil(textWidth(title)) + pad);
    const renderedWidth = rendered?.header[leafIndex] || 0;
    const declared = pixelWidth(column.width) || (renderedWidth ? Math.min(renderedWidth, Math.max(160, headerEstimate * 2)) : 0) || headerEstimate;
    // 固定列和没有表头的列保持原样；操作列可收窄，按钮自动换行。
    if (Boolean(column.fixed) && !isAction || (!title && !hasRichTitle)) {
      leaves.push({ declared, min: declared, want: declared, locked: true });
      return;
    }
    if (isAction) {
      // 至少保留两枚按钮一行的宽度，避免按钮一个一行把整行撑得很高。
      const min = declared > 130 ? Math.max(124, Math.round(declared * 0.6)) : declared;
      leaves.push({ declared, min, want: declared, locked: true });
      return;
    }
    const headerWidth = (title ? textWidth(title.replace(/\|/g, "")) : 78) + (column.sorter ? 18 : 0) + (column.filters ? 18 : 0);
    // 长表头允许折成三行，短表头两行。
    const headerLines = title.length >= 6 ? 3 : 2;
    const headerMin = Math.ceil(headerWidth / headerLines) + pad;
    let typical: number;
    let wide: number;
    let unbreakable = false;
    let solid = 0;
    if (rendered && rendered.typical.length && rendered.typical[leafIndex] !== undefined) {
      typical = rendered.typical[leafIndex];
      wide = rendered.wide[leafIndex];
      unbreakable ||= rendered.numeric[leafIndex];
      solid = rendered.solid[leafIndex];
    } else if (dataIndex !== undefined) {
      const texts = sample.map((row) => cellText(row, dataIndex)).filter(Boolean);
      const contentWidths = texts.map(textWidth);
      typical = percentile(contentWidths, 0.5);
      wide = percentile(contentWidths, 0.9);
      const solidTexts = texts.filter((text) => UNBREAKABLE_TEXT.test(text));
      const rigidTexts = solidTexts.filter((text) => !splitsInTwo(text));
      unbreakable ||= texts.length > 0 && rigidTexts.length / texts.length >= 0.8;
      solid = percentile(solidTexts.map((text) => unbreakableWidth(text)), 0.9);
    } else {
      // 自定义渲染且还没渲染出数据时，最多收窄到原宽的一半，长内容换行。
      const min = Math.min(declared, Math.max(FIT_MIN_COLUMN_WIDTH, headerMin, Math.round(declared * 0.45)));
      leaves.push({ declared, min, want: declared, locked: false });
      return;
    }
    // 金额、日期、编号至少放下九成数据的整行；文字统一折行（最多两行），最小宽度保证九成数据两行内放下；理想宽度让九成数据一行放下。
    // 人名、状态这类短文字（约五个字以内）不拆行。
    const textMin = wide <= 68 ? Math.ceil(wide) : Math.max(68, Math.ceil(Math.min(Math.max(typical, wide), 180) * 0.5));
    const contentMin = unbreakable ? Math.ceil(solid || wide) : Math.max(textMin, Math.ceil(solid));
    const totalMin = rendered?.totals[leafIndex] || 0;
    const min = Math.max(FIT_MIN_COLUMN_WIDTH, headerMin, contentMin + pad, totalMin ? totalMin + pad : 0);
    const want = Math.max(min, Math.ceil(Math.max(headerWidth, wide)) + pad);
    // 金额、日期、编号（包括合计金额）的最小宽度不受原列宽限制，原列宽偏窄时宁可放不下也不截断；文字列最多收窄到原列宽。
    const finalMin = unbreakable || totalMin ? min : Math.min(min, declared);
    leaves.push({ declared: Math.max(declared, finalMin), min: finalMin, want: Math.min(want, Math.max(declared, finalMin)), locked: false, numeric: unbreakable });
  });
  visit(columns);
  return leaves;
}

function leafDeclaredTotal<RecordType extends object>(columns: TableColumnsType<RecordType>): number {
  return columns.reduce((sum, column) => sum + ("children" in column && column.children?.length
    ? leafDeclaredTotal(column.children)
    : typeof column.width === "number" ? column.width : 0), 0);
}

function applyLeafWidths<RecordType extends object>(columns: TableColumnsType<RecordType>, widths: number[]): TableColumnsType<RecordType> {
  let index = 0;
  const visit = (items: TableColumnsType<RecordType>): TableColumnsType<RecordType> => items.map((column) => {
    if ("children" in column && column.children?.length) return { ...column, children: visit(column.children) };
    const width = widths[index++];
    return width && width !== pixelWidth(column.width) ? { ...column, width } : column;
  });
  return visit(columns);
}

// 排查用：页面上设置 window.__oaFitDebug = [] 后记录每张表的自适应判断，平时不产生任何开销。
function recordFit(detail: Record<string, unknown>) {
  const sink = (globalThis as { __oaFitDebug?: unknown[] }).__oaFitDebug;
  if (Array.isArray(sink)) sink.push(detail);
}

function storedWidths(key: string): Record<string, number> {
  const saved = sessionStorage.getItem(key);
  if (!saved) return {};
  const value: unknown = JSON.parse(saved);
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(Object.entries(value).filter(([, width]) => typeof width === "number" && Number.isFinite(width) && width >= MIN_COLUMN_WIDTH && width <= 2000));
}

function ResizableTable<RecordType extends object>({ columns, className, resizable = true, fitStack, fitStackAware, summary, ...props }: ResizableTableProps<RecordType>) {
  const stackBlocked = (Boolean(summary) && !fitStackAware?.summary)
    || (Boolean(props.components?.header) && !fitStackAware?.header)
    || (Boolean(props.components?.body) && !fitStackAware?.body);
  const allowedStack = stackBlocked ? undefined : fitStack;
  const storageKey = useMemo(() => {
    const route = new URLSearchParams(window.location.search).get("page") || window.location.pathname;
    return `sunhold:table-widths:${route}:${className || ""}:${columnSignature(columns || [])}`;
  }, [className, columns]);
  const [widths, setWidths] = useState<Record<string, number>>(() => resizable ? storedWidths(storageKey) : {});
  const widthsRef = useRef(widths);
  const previousStorageKey = useRef({ key: storageKey, resizable });
  const activeResize = useRef<ResizeSession | null>(null);
  const ignoredClick = useRef<string | null>(null);
  const tableRef = useRef<TableHandle | null>(null);
  const observedTable = useRef<{ element: HTMLElement; observer: ResizeObserver } | null>(null);
  const [availableWidth, setAvailableWidth] = useState(0);
  const [renderedStats, setRenderedStats] = useState<RenderedStats | null>(null);
  const renderedKey = useRef("");

  useEffect(() => () => activeResize.current?.stop(), []);
  // 表格节点可能晚于本组件出现或被重新创建，每次渲染后确认观察的是当前节点。
  useEffect(() => {
    const element = tableRef.current?.nativeElement;
    if (!element || typeof ResizeObserver === "undefined" || observedTable.current?.element === element) return;
    observedTable.current?.observer.disconnect();
    const observer = new ResizeObserver(([entry]) => setAvailableWidth(Math.floor(entry.contentRect.width)));
    observer.observe(element);
    observedTable.current = { element, observer };
  });
  useEffect(() => () => {
    observedTable.current?.observer.disconnect();
    observedTable.current = null;
  }, []);
  useEffect(() => {
    if (previousStorageKey.current.key === storageKey && previousStorageKey.current.resizable === resizable) return;
    previousStorageKey.current = { key: storageKey, resizable };
    activeResize.current?.stop();
    const nextWidths = resizable ? storedWidths(storageKey) : {};
    widthsRef.current = nextWidths;
    setWidths(nextWidths);
  }, [storageKey, resizable]);

  const resizedColumns = useMemo((): TableColumnsType<RecordType> | undefined => {
    if (!columns) return undefined;
    // 自适应表格保留比例列宽，不读取历史像素宽度或添加拖拽事件。
    if (!resizable) return columns;
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
  }, [columns, widths, resizable]);

  const userResized = resizable && Object.keys(widths).length > 0;
  const fit = useMemo(() => {
    // 没设横向滚动宽度的表格按列宽之和判断是否超出。
    const declaredX = props.scroll?.x === undefined && resizedColumns ? leafDeclaredTotal(resizedColumns) : props.scroll?.x;
    if (userResized || !resizedColumns || typeof declaredX !== "number" || !declaredX || availableWidth <= 0) {
      recordFit({ className, skip: userResized ? "resized" : typeof declaredX !== "number" ? `x=${String(declaredX)}` : availableWidth <= 0 ? "unmeasured" : "nocolumns" });
      return null;
    }
    const selectionWidth = props.rowSelection ? (typeof props.rowSelection.columnWidth === "number" ? props.rowSelection.columnWidth : 40) : 0;
    const expandWidth = props.expandable ? 48 : 0;
    const scrollbarWidth = props.scroll?.y ? 12 : 0;
    const usable = availableWidth - selectionWidth - expandWidth - scrollbarWidth - 2;
    const leaves = measureLeaves(resizedColumns, (props.dataSource || []) as readonly RecordType[], renderedStats);
    const declaredTotal = Math.max(declaredX - selectionWidth - expandWidth, leaves.reduce((sum, leaf) => sum + leaf.declared, 0));
    if (usable >= declaredTotal) {
      recordFit({ className, skip: "fits", usable, declaredTotal });
      return null;
    }
    const solve = (candidate: FitLeaf[]) => {
      const minTotal = candidate.reduce((sum, leaf) => sum + leaf.min, 0);
      if (minTotal > usable) return null;
      const wantTotal = candidate.reduce((sum, leaf) => sum + leaf.want, 0);
      // 先满足每列的理想宽度；放不下时按“理想-最小”的余量等比收缩，空间富余时由表格按比例撑满。
      const shrink = wantTotal > usable ? (wantTotal - usable) / Math.max(1, wantTotal - minTotal) : 0;
      return candidate.map((leaf) => Math.floor(leaf.want - (leaf.want - leaf.min) * shrink));
    };
    const describe = (candidate: FitLeaf[]) => candidate.map((leaf) => `${leaf.declared}/${leaf.min}/${leaf.want}${leaf.locked ? "L" : ""}`).join(" ");
    // 依次尝试：正常间距 → 紧凑间距 → 叠放相关列（仅声明了 fitStack 的表）。
    let widths = solve(leaves);
    if (widths) {
      recordFit({ className, fit: "normal", usable, widths: widths.join(" "), leaves: describe(leaves) });
      return { columns: applyLeafWidths(resizedColumns, widths), x: usable, dense: false, stacked: false, layout: undefined, groups: undefined };
    }
    const denseLeaves = measureLeaves(resizedColumns, (props.dataSource || []) as readonly RecordType[], renderedStats, FIT_DENSE_PADDING);
    widths = solve(denseLeaves);
    if (widths) {
      recordFit({ className, fit: "dense", usable, widths: widths.join(" "), leaves: describe(denseLeaves) });
      return { columns: applyLeafWidths(resizedColumns, widths), x: usable, dense: true, stacked: false, layout: undefined, groups: undefined };
    }
    if (allowedStack?.length) {
      // 按 fitStack 的先后顺序逐个加入分组，只叠放到刚好放得下为止，其余列仍逐列显示。
      let stacked = stackColumns(resizedColumns, denseLeaves, allowedStack);
      for (let count = 1; count <= allowedStack.length; count += 1) {
        const groups = allowedStack.slice(0, count);
        stacked = stackColumns(resizedColumns, denseLeaves, groups);
        widths = solve(stacked.leaves);
        if (widths) {
          recordFit({ className, fit: "stacked", groups: count, usable, widths: widths.join(" "), leaves: describe(stacked.leaves) });
          return { columns: applyLeafWidths(stacked.columns, widths), x: usable, dense: true, stacked: true, layout: stacked.layout, groups };
        }
      }
      recordFit({ className, usable, declaredTotal, minTotal: stacked.leaves.reduce((sum, leaf) => sum + leaf.min, 0), leaves: describe(stacked.leaves), stage: "stacked" });
      return null;
    }
    recordFit({ className, usable, declaredTotal, minTotal: denseLeaves.reduce((sum, leaf) => sum + leaf.min, 0), leaves: describe(denseLeaves) });
    return null;
  }, [userResized, resizedColumns, allowedStack, props.scroll?.x, props.scroll?.y, props.rowSelection, props.expandable, props.dataSource, availableWidth, renderedStats]);
  const fitLayout = useRef<(number | number[])[] | undefined>(undefined);
  fitLayout.current = fit?.layout;

  // 数据渲染后再按真实单元格文字校准一次列宽；文字没变就不再触发重算。
  useEffect(() => {
    if (userResized || !resizedColumns || (props.scroll?.x !== undefined && typeof props.scroll?.x !== "number")) return;
    const schedule = typeof window.requestAnimationFrame === "function" ? window.requestAnimationFrame.bind(window) : (callback: () => void) => setTimeout(callback, 16) as unknown as number;
    const cancel = typeof window.cancelAnimationFrame === "function" ? window.cancelAnimationFrame.bind(window) : (frame: number) => clearTimeout(frame);
    const frame = schedule(() => {
      const leafCount = measureLeaves(resizedColumns, [], null).length;
      // 叠放后按叠放布局把每一行的值还原到原来的列上再测量。
      const stats = readRenderedStats(tableRef.current?.nativeElement, leafCount, fitLayout.current);
      const key = stats ? JSON.stringify(stats) : "";
      if (key === renderedKey.current) return;
      renderedKey.current = key;
      setRenderedStats(stats);
    });
    return () => cancel(frame);
  }, [userResized, props.dataSource, resizedColumns, props.scroll?.x]);

  const scroll = userResized && typeof props.scroll?.x === "number"
    ? { ...props.scroll, x: "max-content" as const }
    : fit ? { ...props.scroll, x: fit.x } : props.scroll;
  const sticky = props.sticky ?? (scroll?.x !== undefined ? { offsetScroll: 0 } : undefined);
  // 列被叠放时，把叠放分组告诉自定义表头/表体（例如合计行），让它们按同样的方式合并单元格。
  const stackGroups: FitStackSpec = useMemo(
    () => (fit?.groups ? fit.groups.map((group) => ({ keys: group.keys, labels: group.labels })) : []),
    [fit?.groups],
  );
  const stackSpec = stackGroups.length ? JSON.stringify(stackGroups) : "";
  const tableComponents = props.components;
  const components = useMemo(() => {
    if (!stackSpec || !tableComponents) return tableComponents;
    const withStack = (section: unknown) => {
      if (!section || typeof section !== "object" || Array.isArray(section)) return section;
      const wrapper = (section as { wrapper?: unknown }).wrapper;
      if (!wrapper) return section;
      const Wrapper = wrapper as (wrapperProps: Record<string, unknown>) => ReactNode;
      return { ...section, wrapper: (wrapperProps: Record<string, unknown>) => <Wrapper {...wrapperProps} data-oa-stack={stackSpec} /> };
    };
    return { ...tableComponents, header: withStack(tableComponents.header), body: withStack(tableComponents.body) };
  }, [tableComponents, stackSpec]);
  const locale = props.loading
    ? { ...props.locale, emptyText: <span className="oa-table-loading-empty">正在加载数据…</span> }
    : props.locale;
  const stackedNow = Boolean(fit?.stacked);
  const tableSummary = summary ? (data: readonly RecordType[]) => summary(data, { stacked: stackedNow, groups: stackGroups }) : undefined;
  return <AntTable<RecordType> {...props} summary={tableSummary} components={components as TableProps<RecordType>["components"]} ref={tableRef as never} locale={locale} scroll={scroll} sticky={sticky} className={[className, resizable ? "oa-resizable-table" : "", fit ? "oa-fit-table" : "", fit?.dense ? "oa-fit-dense" : ""].filter(Boolean).join(" ")} columns={fit ? fit.columns : resizedColumns} />;
}

const Table = Object.assign(ResizableTable, {
  Column: AntTable.Column,
  ColumnGroup: AntTable.ColumnGroup,
  Summary: AntTable.Summary,
  SELECTION_COLUMN: AntTable.SELECTION_COLUMN,
  EXPAND_COLUMN: AntTable.EXPAND_COLUMN,
}) as typeof AntTable & typeof ResizableTable;

export default Table;
