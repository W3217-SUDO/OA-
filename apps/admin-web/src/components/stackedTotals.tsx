import type { ReactNode } from "react";
import type { FitStackSpec } from "./ResizableTable";

// 宽表在一屏放不下时会把相关列叠放到一个单元格里（见 ResizableTable 的 fitStack）。
// 合计行是按“每列一个单元格”手写的，这里按同样的叠放布局重新排列合计单元格，保证合计始终对齐表头。

export type TotalCell = { key: string; content: ReactNode };

// 自定义表体/表头会收到 data-oa-stack 属性（JSON），取出叠放布局并把它从要渲染到 DOM 的属性里去掉。
export function takeTotalsStack<Props extends object>(props: Props): [FitStackSpec, Omit<Props, "data-oa-stack">] {
  const { "data-oa-stack": attribute, ...rest } = props as Props & { "data-oa-stack"?: unknown };
  if (typeof attribute !== "string" || !attribute) return [[], rest];
  try {
    const parsed: unknown = JSON.parse(attribute);
    return [Array.isArray(parsed) ? parsed as FitStackSpec : [], rest];
  } catch {
    return [[], rest];
  }
}

// ids 是表格各数据列的标识（与 ResizableTable 一致：key，其次 dataIndex，再次文字表头），content(i) 返回第 i 列的合计内容。
export function layoutTotalCells(ids: readonly string[], stack: FitStackSpec | undefined, content: (index: number) => ReactNode): TotalCell[] {
  const groups = stack ?? [];
  const cells: TotalCell[] = [];
  ids.forEach((id, index) => {
    const group = groups.find((item) => item.keys.includes(id));
    if (!group) {
      cells.push({ key: `${id}-${index}`, content: content(index) });
      return;
    }
    if (group.keys[0] !== id) return;
    const values = group.keys.map((key) => {
      const memberIndex = ids.indexOf(key);
      return memberIndex >= 0 ? content(memberIndex) : null;
    });
    const empty = values.every((value) => value === null || value === undefined || value === "");
    cells.push({
      key: group.keys.join("+"),
      content: empty ? null : (
        <div className={`oa-stack-cell${group.labels ? " has-labels" : ""}`}>
          {values.map((value, memberIndex) => (
            <div className="oa-stack-line" key={group.keys[memberIndex]}>
              {group.labels && <span className="oa-stack-label">{group.labels[memberIndex]}</span>}
              <span className="oa-stack-value is-number">{value}</span>
            </div>
          ))}
        </div>
      ),
    });
  });
  return cells;
}

// 各列的标识，和 ResizableTable 判断叠放分组时用的规则一致。
export function columnIds(columns: readonly object[]): string[] {
  return columns.map((column) => {
    const record = column as { key?: unknown; dataIndex?: unknown; title?: unknown };
    if (record.key !== undefined && record.key !== null) return String(record.key);
    if (record.dataIndex !== undefined && record.dataIndex !== null) return Array.isArray(record.dataIndex) ? record.dataIndex.join(".") : String(record.dataIndex);
    return typeof record.title === "string" ? record.title : "";
  });
}
