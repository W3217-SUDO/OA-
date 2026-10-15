import { Button } from "antd";
import type { TableColumnsType } from "antd";
import { caseFeeRefundLabel } from "../../caseFeeLegacyProjection.mjs";
import { displayFinancialValue } from "../../financialValueDisplay";
import { caseFeeBillDisplay, caseFeeReceiptApplicable } from "../caseReceiptFiles";
import type { CaseRow } from "../types";

type ExternalCaseFeeColumnContext = {
    readonly viewingCounselCase: CaseRow | null;
    readonly openRelatedContract: (target: unknown) => void;
    readonly casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
    readonly openRelatedIncomingPayment: (fee: CaseRow) => void;
    readonly openRelatedInvoice: (fee: CaseRow) => void;
    readonly openCaseReceiptFiles: (fee: CaseRow) => void;
};

const firmColumnWeights = [10.5, 13, 7, 8, 6.5, 8, 8, 8, 8, 7, 12];
const firmColumnWeightTotal = firmColumnWeights.reduce((total, weight) => total + weight, 0);
const firmColumnWidths = firmColumnWeights.map(weight => `${(weight / firmColumnWeightTotal * 96).toFixed(3)}%`);

function formatAmount(value: unknown): string {
    const amount = Number(value ?? 0);
    return Number.isFinite(amount) ? amount.toFixed(2) : "—";
}

function formatRefund(data: Record<string, unknown>): string {
    if (data.refund_display_suppressed) return "0.00";
    const label = caseFeeRefundLabel(data);
    const match = label.match(/^(-?\d+(?:\.\d+)?)(.*)$/);
    return match ? `${formatAmount(match[1])}${match[2]}` : label;
}

function createColumns(context: ExternalCaseFeeColumnContext, firm: boolean): TableColumnsType<CaseRow> {
    const columns: TableColumnsType<CaseRow> = [
        { title: "合同编号", width: 150, render: (_: unknown, row: CaseRow) => {
                const contractNo = row.data.contract_no || context.viewingCounselCase?.data.contract_no;
                const contractId = Number(row.data.contract_id || row.data.contract_record_id || context.viewingCounselCase?.data.contract_id || context.viewingCounselCase?.data.contract_record_id || 0) || undefined;
                return contractNo ? <Button type="link" className="case-cell-link" onClick={() => context.openRelatedContract({ id: contractId, serial_no: contractNo })}>{contractNo}</Button> : "—";
            } },
        { title: "费用类型", width: 190, render: (_: unknown, row: CaseRow) => {
                const name = row.data.expense_subtype || row.data.fee_type || row.title || "—";
                const code = String(row.data.fee_type_code || "").trim();
                return firm && code ? `(${code}) ${name}` : name;
            } },
        { title: "金额", width: 100, align: "right" as const, render: (_: unknown, row: CaseRow) => firm ? formatAmount(row.data.amount) : displayFinancialValue(row.data.amount ?? 0) },
        { title: "退费", width: 110, align: "right" as const, render: (_: unknown, row: CaseRow) => firm ? formatRefund(row.data) : caseFeeRefundLabel(row.data) },
        { title: "提交人", width: 120, render: (_: unknown, row: CaseRow) => row.data.submitter_display_name || row.data.submitted_by_display_name || row.data.handler_display_name || row.owner_display_name || context.casePersonDisplayName(row.owner) },
        { title: "提交日期", width: 120, render: (_: unknown, row: CaseRow) => displayFinancialValue(String(row.data.submitted_at || row.created_at || row.data.created_at || "")).slice(0, 10) || "—" },
        { title: "回款日期", width: 120, render: (_: unknown, row: CaseRow) => caseFeeReceiptApplicable(row.data, row.title)
            ? displayFinancialValue(String(row.data.received_at || row.data.cashed_date || "")).slice(0, 10) || "—" : "—" },
        { title: "回款金额", width: 110, align: "right" as const, render: (_: unknown, row: CaseRow) => {
                if (!caseFeeReceiptApplicable(row.data, row.title)) return "—";
                const rawValue = row.data.received_amount ?? row.data.cashed_amount;
                const normalizedValue = String(rawValue ?? "").trim();
                const value = normalizedValue && normalizedValue !== "/" && normalizedValue !== "\\"
                    ? Number(normalizedValue)
                    : 0;
                if (!Number.isFinite(value)) return firm ? "—" : 0;
                return value !== 0
                    ? <Button type="link" className={firm ? "case-cell-link case-firm-fee-amount-link" : "case-cell-link"} onClick={() => context.openRelatedIncomingPayment(row)}>{firm ? formatAmount(value) : value}</Button>
                    : firm ? "0.00" : 0;
            } },
        { title: "开票日期", width: 160, render: (_: unknown, row: CaseRow) => {
                const { dates } = caseFeeBillDisplay(row.data);
                return dates.length ? <div>{dates.map(date => <div key={date}>{date}</div>)}</div> : "—";
            } },
        { title: "发票号", width: 220, render: (_: unknown, row: CaseRow) => {
                const { entries } = caseFeeBillDisplay(row.data, firm ? { preferFileBillNo: true } : undefined);
                return entries.length ? <div>{entries.map(entry => <div key={entry.key}>
                    <Button type="link" className="case-cell-link" title={firm ? entry.title : entry.label}
                        style={{ maxWidth: "100%", height: "auto", whiteSpace: "normal", overflowWrap: "anywhere", textAlign: "left" }}
                        onClick={() => entry.kind === "invoice" ? context.openRelatedInvoice(row) : context.openCaseReceiptFiles(row)}>{entry.label}</Button>
                </div>)}</div> : "—";
            } },
        { title: "申请付款金额", width: 130, align: "right" as const, render: (_: unknown, row: CaseRow) => firm ? formatAmount(row.data.payment_requested_amount) : displayFinancialValue(row.data.payment_requested_amount ?? 0) },
    ];
    if (!firm) return columns;
    return columns.map((column, index) => ({
        ...column,
        width: firmColumnWidths[index],
        onCell: (row, rowIndex) => {
            const cell = column.onCell?.(row, rowIndex);
            return {
                ...cell,
                className: [cell?.className, "case-firm-fee-cell"].filter(Boolean).join(" "),
                "data-label": String(column.title || ""),
            };
        },
    }));
}

export function createExternalCaseFeeColumns(context: ExternalCaseFeeColumnContext) {
    return createColumns(context, false);
}

export function createFirmCaseFeeColumns(context: ExternalCaseFeeColumnContext) {
    return createColumns(context, true);
}
