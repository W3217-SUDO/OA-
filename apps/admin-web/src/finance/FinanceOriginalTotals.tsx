import type { ComponentProps } from "react";
import Table from "../components/ResizableTable";
import type { FitStackSpec } from "../components/ResizableTable";
import { layoutTotalCells, takeTotalsStack } from "../components/stackedTotals";
import { paymentQueryPageTotal } from "./constants";
import type { FinanceFeeQueryMeta, FinanceInternalQueueMeta, OriginalFinanceRow } from "./types";

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

// 传入 columnIds 时按列对齐（勾选列 + 各数据列，金额放在“申请金额”列下），并跟随表格的叠放布局；未传时保持原有排列。
export function PaymentQueryTotalBody({ rows, columnCount, columnIds, children, ...bodyProps }: TotalBodyProps & {
  rows: TotalRows;
  columnCount: number;
  columnIds?: readonly string[];
}) {
  const [stack, domProps] = takeTotalsStack(bodyProps);
  return <tbody {...domProps}>
    <tr className="finance-payment-query-page-total">
      {columnIds
        ? [<td key="payment-query-total-selection" />, ...layoutTotalCells(columnIds, stack, (index) => columnIds[index] === "申请金额" ? paymentQueryPageTotal(rows) : null)
          .map((cell) => <td key={cell.key}>{cell.content}</td>)]
        : Array.from({ length: columnCount }, (_column, index) => <td key={`payment-query-total-${index}`}>
          {index === 4 ? paymentQueryPageTotal(rows) : null}
        </td>)}
    </tr>
    {children}
  </tbody>;
}

export function PaymentQueryPageSummary({ rows, columnCount, columnIds, stack }: { rows: TotalRows; columnCount: number; columnIds?: readonly string[]; stack?: FitStackSpec }) {
  if (!rows.length) return null;
  return <Table.Summary.Row className="finance-payment-query-page-total-bottom">
    {columnIds
      ? [<Table.Summary.Cell key="payment-query-summary-selection" index={0} />, ...layoutTotalCells(columnIds, stack, (index) => columnIds[index] === "申请金额" ? paymentQueryPageTotal(rows) : null)
        .map((cell, position) => <Table.Summary.Cell key={cell.key} index={position + 1}>{cell.content}</Table.Summary.Cell>)]
      : Array.from({ length: columnCount }, (_column, index) => <Table.Summary.Cell key={`payment-query-summary-${index}`} index={index}>
        {index === 4 ? paymentQueryPageTotal(rows) : null}
      </Table.Summary.Cell>)}
  </Table.Summary.Row>;
}

// 列标识与配置列一致（表头-序号），用于按表格叠放布局排列合计单元格。
const headerIds = (headers: readonly string[]) => headers.map((header, index) => `${header}-${index}`);

export function FeeQueryTotalBody({ headers, totals, children, ...bodyProps }: TotalBodyProps & {
  headers: string[];
  totals: FinanceFeeQueryMeta["totals"];
}) {
  const [stack, domProps] = takeTotalsStack(bodyProps);
  return <tbody {...domProps}>
    <tr className="finance-fee-query-grand-total">
      <td />
      {layoutTotalCells(headerIds(headers), stack, (index) => {
        const key = feeTotalKeys[headers[index]];
        const value = key ? totals[key] : null;
        return value == null ? null : Number(value).toFixed(2);
      }).map((cell) => <td key={cell.key}>{cell.content}</td>)}
    </tr>
    {children}
  </tbody>;
}

export function FeeQueryPageSummary({ rows, headers, stack }: { rows: TotalRows; headers: string[]; stack?: FitStackSpec }) {
  if (!rows.length) return null;
  return <Table.Summary.Row className="finance-fee-query-page-total">
    <Table.Summary.Cell index={0} />
    {layoutTotalCells(headerIds(headers), stack, (index) => {
      const key = feeTotalKeys[headers[index]];
      return key ? rows.reduce((sum, row) => sum + Number(row.data?.[key] || 0), 0).toFixed(2) : null;
    }).map((cell, position) => <Table.Summary.Cell key={cell.key} index={position + 1}>{cell.content}</Table.Summary.Cell>)}
  </Table.Summary.Row>;
}

export function InternalQueueSummary({ meta, headers, selectable, stack }: { meta: FinanceInternalQueueMeta; headers: string[]; selectable: boolean; stack?: FitStackSpec }) {
  const amounts: Record<string, number | null | undefined> = {
    金额: meta.totalAmount, 申请金额: meta.totalAmount, 实际提成: meta.totalActualCommission, 到账金额: meta.totalCashedAmount,
  };
  headers.forEach((header) => {
    const amount = amounts[header];
    const missingAmount = meta.amountTotalsComplete === false && amount === null;
    if (header in amounts && meta.amountVisible && !Number.isFinite(amount) && !missingAmount) throw new Error("内部费用汇总响应无效");
  });
  return <Table.Summary.Row className="finance-internal-list-summary">
    {selectable && <Table.Summary.Cell index={0} />}
    {layoutTotalCells(headerIds(headers), stack, (index) => {
      const header = headers[index];
      const amount = amounts[header];
      const missingAmount = meta.amountTotalsComplete === false && amount === null;
      return header in amounts ? meta.amountVisible ? missingAmount ? "待核对" : amount!.toFixed(2) : "无权限" : index === 0 ? "合计" : null;
    }).map((cell, position) => <Table.Summary.Cell key={cell.key} index={position + Number(selectable)}>{cell.content}</Table.Summary.Cell>)}
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
