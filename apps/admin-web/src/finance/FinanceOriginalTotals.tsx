import type { ComponentProps } from "react";
import Table from "../components/ResizableTable";
import { paymentQueryPageTotal } from "./constants";
import type { FinanceFeeQueryMeta, OriginalFinanceRow } from "./types";

type TotalBodyProps = ComponentProps<"tbody">;
type TotalRows = readonly OriginalFinanceRow[];

const feeTotalKeys: Record<string, string> = {
  金额: "amount",
  退费金额: "refund_requested_amount",
  已退金额: "refunded_amount",
  到账金额: "cashed_amount",
  付款金额: "paid_amount",
};

const packageTotal = (rows: TotalRows) => rows.reduce(
  (sum, row) => sum + Number(row.data?.total_amount ?? row.data?.amount ?? 0),
  0,
).toFixed(2);

export function PaymentQueryTotalBody({ rows, columnCount, children, ...bodyProps }: TotalBodyProps & {
  rows: TotalRows;
  columnCount: number;
}) {
  return <tbody {...bodyProps}>
    <tr className="finance-payment-query-page-total">
      {Array.from({ length: columnCount }, (_column, index) => <td key={`payment-query-total-${index}`}>
        {index === 4 ? paymentQueryPageTotal(rows) : null}
      </td>)}
    </tr>
    {children}
  </tbody>;
}

export function PaymentQueryPageSummary({ rows, columnCount }: { rows: TotalRows; columnCount: number }) {
  if (!rows.length) return null;
  return <Table.Summary.Row className="finance-payment-query-page-total-bottom">
    {Array.from({ length: columnCount }, (_column, index) => <Table.Summary.Cell key={`payment-query-summary-${index}`} index={index}>
      {index === 4 ? paymentQueryPageTotal(rows) : null}
    </Table.Summary.Cell>)}
  </Table.Summary.Row>;
}

export function FeeQueryTotalBody({ headers, totals, children, ...bodyProps }: TotalBodyProps & {
  headers: string[];
  totals: FinanceFeeQueryMeta["totals"];
}) {
  return <tbody {...bodyProps}>
    <tr className="finance-fee-query-grand-total">
      <td />
      {headers.map((header, index) => {
        const key = feeTotalKeys[header];
        const value = key ? totals[key] : null;
        return <td key={`${header}-${index}`}>{value == null ? null : Number(value).toFixed(2)}</td>;
      })}
    </tr>
    {children}
  </tbody>;
}

export function FeeQueryPageSummary({ rows, headers }: { rows: TotalRows; headers: string[] }) {
  if (!rows.length) return null;
  return <Table.Summary.Row className="finance-fee-query-page-total">
    <Table.Summary.Cell index={0} />
    {headers.map((header, index) => {
      const key = feeTotalKeys[header];
      return <Table.Summary.Cell key={`${header}-${index}`} index={index + 1}>
        {key ? rows.reduce((sum, row) => sum + Number(row.data?.[key] || 0), 0).toFixed(2) : null}
      </Table.Summary.Cell>;
    })}
  </Table.Summary.Row>;
}

export function InternalPaymentPageSummary({ rows, headers }: { rows: TotalRows; headers: string[] }) {
  return <Table.Summary.Row className="finance-internal-list-summary">
    <Table.Summary.Cell index={0} />
    {headers.map((header, index) => <Table.Summary.Cell key={header} index={index + 1}>
      {header === "实际提成"
        ? rows.reduce((sum, row) => sum + Number(row.data?.actual_commission ?? row.data?.amount ?? 0), 0).toFixed(2)
        : null}
    </Table.Summary.Cell>)}
  </Table.Summary.Row>;
}

export function PaymentPackageTotalBody({ rows, headers, children, ...bodyProps }: TotalBodyProps & {
  rows: TotalRows;
  headers: string[];
}) {
  return <tbody {...bodyProps}>
    <tr className="finance-payment-package-grand-total">
      {headers.map((header, index) => <td key={`${header}-${index}`}>
        {header === "付款总金额" ? packageTotal(rows) : null}
      </td>)}
    </tr>
    {children}
  </tbody>;
}

export function PaymentPackagePageSummary({ rows, headers }: { rows: TotalRows; headers: string[] }) {
  return <Table.Summary.Row className="finance-payment-package-summary">
    {headers.map((header, index) => <Table.Summary.Cell key={header} index={index}>
      {header === "付款总金额" ? packageTotal(rows) : null}
    </Table.Summary.Cell>)}
  </Table.Summary.Row>;
}
