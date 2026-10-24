import type { ComponentProps } from "react";

type StackSpec = { keys: string[]; labels?: string[] }[];

function totalText(header: string, totals: Record<string, number | null>) {
  return header === "操作" ? "合计" : totals[header] == null
    ? ["已分官费", "已分代理费", "已分其他费"].includes(header) ? "未知" : null
    : totals[header]!.toFixed(2);
}

export function IncomingTotalsBody({ headers, totals, children, ...props }: ComponentProps<"tbody"> & {
  headers: string[];
  totals: Record<string, number | null>;
}) {
  // 一屏放不下时表格会把相关金额列叠放成一个单元格，合计行跟着同样合并。
  const { "data-oa-stack": stackAttribute, ...bodyProps } = props as ComponentProps<"tbody"> & { "data-oa-stack"?: string };
  let stack: StackSpec = [];
  try {
    stack = stackAttribute ? JSON.parse(stackAttribute) as StackSpec : [];
  } catch {
    stack = [];
  }
  const keyOf = (header: string, index: number) => `${header}-${index}`;
  const groupOf = (key: string) => stack.find((group) => group.keys.includes(key));
  return <tbody {...bodyProps}>
    <tr className="finance-incoming-grand-total">
      <td />
      {headers.map((header, index) => {
        const key = keyOf(header, index);
        const group = groupOf(key);
        if (!group) return <td key={key}>{totalText(header, totals)}</td>;
        if (group.keys[0] !== key) return null;
        return <td key={key}>
          <div className={`oa-stack-cell${group.labels ? " has-labels" : ""}`}>
            {group.keys.map((memberKey, memberIndex) => {
              const memberHeader = headers[headers.findIndex((item, itemIndex) => keyOf(item, itemIndex) === memberKey)];
              return <div className="oa-stack-line" key={memberKey}>
                {group.labels && <span className="oa-stack-label">{group.labels[memberIndex]}</span>}
                <span className="oa-stack-value is-number">{memberHeader ? totalText(memberHeader, totals) : null}</span>
              </div>;
            })}
          </div>
        </td>;
      })}
    </tr>
    {children}
  </tbody>;
}
