import { Button, Space } from "antd";
import { caseFeeRefundLabel } from "../../caseFeeLegacyProjection.mjs";
import { caseReceiptFiles } from "../caseReceiptFiles";
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
        { title: "通知日期", width: 120, render: (_: unknown, row: CaseRow) => String(row.data.inform_date || row.data.notice_date || "").slice(0, 10) || "—" },
        { title: "回款日期", width: 120, render: (_: unknown, row: CaseRow) => String(row.data.received_at || row.data.cashed_date || "").slice(0, 10) || "—" },
        { title: "回款金额", width: 110, align: "right" as const, render: (_: unknown, row: CaseRow) => {
                const value = row.data.received_amount ?? row.data.cashed_amount;
                return Number(value || 0) !== 0 ? <Button type="link" className="case-cell-link" onClick={() => context.openRelatedIncomingPayment(row)}>{value}</Button> : value ?? "/";
            } },
        { title: "开票日期", width: 160, render: (_: unknown, row: CaseRow) => {
                const receipts = caseReceiptFiles(row.data);
                const invoiceDate = String(row.data.invoice_date || "").slice(0, 10);
                if (!receipts.length) return invoiceDate || "—";
                return <Space direction="vertical" size={0}>
                    {invoiceDate && <span>开票：{invoiceDate}</span>}
                    {receipts.map((receipt, index) => <span key={`${receipt.attachmentId}-${index}`}>{receipt.billDate || "—"}</span>)}
                </Space>;
            } },
        { title: "发票号", width: 220, render: (_: unknown, row: CaseRow) => {
                const receipts = caseReceiptFiles(row.data);
                if (!row.data.invoice_no && !receipts.length) return "—";
                return <Space direction="vertical" size={0}>
                    {row.data.invoice_no && <Button type="link" className="case-cell-link" onClick={() => context.openRelatedInvoice(row)}>{row.data.invoice_no}</Button>}
                    {receipts.map((receipt, index) => receipt.attachmentId > 0
                        ? <Button key={`${receipt.attachmentId}-${index}`} type="link" className="case-cell-link" onClick={() => context.openCaseReceiptFiles(row)}>{receipt.billNo || `文件${index + 1}`}</Button>
                        : <span key={`missing-${index}`}>{receipt.billNo || `文件${index + 1}`}（附件缺失）</span>)}
                </Space>;
            } },
        { title: "申请付款金额", width: 130, align: "right" as const, render: (_: unknown, row: CaseRow) => row.data.payment_requested_amount ?? 0 },
    ];
}
