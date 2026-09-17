import type { ComponentProps } from "react";
import { incomingTotals } from "./incomingTotals.mjs";
import type { IncomingPayment } from "./types";

export function IncomingTotalsBody({ headers, rows, children, ...props }: ComponentProps<"tbody"> & {
  headers: string[];
  rows: IncomingPayment[];
}) {
  const totals = incomingTotals(rows);
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
