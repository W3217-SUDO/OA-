import { Button } from "antd";
import { caseFeeRefundLabel } from "../../caseFeeLegacyProjection.mjs";
import { caseFeeBillDisplay, caseFeeReceiptApplicable } from "../caseReceiptFiles";
import type { CaseRow } from "../types";
export function createExternalCaseFeeColumns(context: {
    readonly viewingCounselCase: CaseRow | null;
    readonly openRelatedContract: (target: unknown) => void;
    readonly casePersonDisplayName: (source: unknown, displayName?: unknown) => string;
    readonly openRelatedIncomingPayment: (fee: CaseRow) => void;
    readonly openRelatedInvoice: (fee: CaseRow) => void;
    readonly openCaseReceiptFiles: (fee: CaseRow) => void;
}) {
    return [
        { title: "合同编号", width: 150, render: (_: unknown, row: CaseRow) => {
                const contractNo = row.data.contract_no || context.viewingCounselCase?.data.contract_no;
                const contractId = Number(row.data.contract_id || row.data.contract_record_id || context.viewingCounselCase?.data.contract_id || context.viewingCounselCase?.data.contract_record_id || 0) || undefined;
                return contractNo ? <Button type="link" className="case-cell-link" onClick={() => context.openRelatedContract({ id: contractId, serial_no: contractNo })}>{contractNo}</Button> : "—";
            } },
        { title: "费用类型", width: 190, render: (_: unknown, row: CaseRow) => row.data.expense_subtype || row.data.fee_type || row.title || "—" },
        { title: "金额", width: 100, align: "right" as const, render: (_: unknown, row: CaseRow) => row.data.amount ?? 0 },
        { title: "退费", width: 110, align: "right" as const, render: (_: unknown, row: CaseRow) => caseFeeRefundLabel(row.data) },
        { title: "提交人", width: 120, render: (_: unknown, row: CaseRow) => row.data.submitter_display_name || row.data.submitted_by_display_name || row.data.handler_display_name || row.owner_display_name || context.casePersonDisplayName(row.owner) },
        { title: "提交日期", width: 120, render: (_: unknown, row: CaseRow) => String(row.data.submitted_at || row.created_at || row.data.created_at || "").slice(0, 10) || "—" },
        { title: "回款日期", width: 120, render: (_: unknown, row: CaseRow) => caseFeeReceiptApplicable(row.data, row.title)
            ? String(row.data.received_at || row.data.cashed_date || "").slice(0, 10) || "—" : "/" },
        { title: "回款金额", width: 110, align: "right" as const, render: (_: unknown, row: CaseRow) => {
                if (!caseFeeReceiptApplicable(row.data, row.title)) return "/";
                const rawValue = row.data.received_amount ?? row.data.cashed_amount;
                const normalizedValue = String(rawValue ?? "").trim();
                const value = normalizedValue && normalizedValue !== "/" && normalizedValue !== "\\"
                    ? Number(normalizedValue)
                    : 0;
                return Number.isFinite(value) && value !== 0
                    ? <Button type="link" className="case-cell-link" onClick={() => context.openRelatedIncomingPayment(row)}>{value}</Button>
                    : 0;
            } },
        { title: "开票日期", width: 160, render: (_: unknown, row: CaseRow) => {
                const { dates } = caseFeeBillDisplay(row.data);
                return dates.length ? <div>{dates.map(date => <div key={date}>{date}</div>)}</div> : "—";
            } },
        { title: "发票号", width: 220, render: (_: unknown, row: CaseRow) => {
                const { entries } = caseFeeBillDisplay(row.data);
                return entries.length ? <div>{entries.map(entry => <div key={entry.key}>
                    <Button type="link" className="case-cell-link" title={entry.label}
                        style={{ maxWidth: "100%", height: "auto", whiteSpace: "normal", overflowWrap: "anywhere", textAlign: "left" }}
                        onClick={() => entry.kind === "invoice" ? context.openRelatedInvoice(row) : context.openCaseReceiptFiles(row)}>{entry.label}</Button>
                </div>)}</div> : "—";
            } },
        { title: "申请付款金额", width: 130, align: "right" as const, render: (_: unknown, row: CaseRow) => row.data.payment_requested_amount ?? 0 },
    ];
}
