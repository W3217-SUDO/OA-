import type { ComponentProps } from "react";

export function IncomingTotalsBody({ headers, totals, children, ...props }: ComponentProps<"tbody"> & {
  headers: string[];
  totals: Record<string, number | null>;
}) {
  return <tbody {...props}>
    <tr className="finance-incoming-grand-total">
      <td />
      {headers.map((header, index) => <td key={`${header}-${index}`}>
        {header === "操作" ? "合计" : totals[header] == null ? null : totals[header].toFixed(2)}
      </td>)}
    </tr>
    {children}
  </tbody>;
}
