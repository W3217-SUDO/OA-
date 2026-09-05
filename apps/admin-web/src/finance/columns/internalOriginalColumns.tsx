import { Button } from "antd";
import { money } from "../constants";
import type { Fee, Transaction } from "../types";
export function createInternalOriginalColumns(context: {
    readonly internalMineOperation: (_: unknown, row: Fee) => React.JSX.Element;
    readonly paymentStatus: (fee: Fee) => any;
    readonly openCaseDetail: (caseNo: unknown) => Promise<void>;
    readonly latestTransaction: (fee: Fee) => Transaction;
    readonly financePersonDisplayName: (identity: unknown, displayName?: unknown) => string;
}) {
    return [
        {
            title: "操作",
            key: "action",
            width: 70,
            render: context.internalMineOperation,
        },
        { title: "请款单号", dataIndex: "serial_no", width: 165 },
        {
            title: "状态",
            width: 95,
            render: (_: unknown, row: Fee) => context.paymentStatus(row),
        },
        {
            title: "申请日期",
            width: 110,
            render: (_: unknown, row: Fee) => (row.data.application_date || row.created_at || "—").slice(0, 10),
        },
        {
            title: "审核日期",
            width: 110,
            render: (_: unknown, row: Fee) => (row.data.audit_date || row.updated_at || "—").slice(0, 10),
        },
        {
            title: "申请金额",
            width: 110,
            render: (_: unknown, row: Fee) => row.data.amount == null ? "—" : money(row.data.amount),
        },
        {
            title: "案件编号",
            width: 145,
            render: (_: unknown, row: Fee) => row.data.case_no ? <Button type="link" onClick={() => context.openCaseDetail(row.data.case_no)}>{row.data.case_no}</Button> : "—",
        },
        {
            title: "案件阶段",
            width: 105,
            render: (_: unknown, row: Fee) => row.data.case_stage || "—",
        },
        { title: "案件名称", dataIndex: "title", width: 190 },
        {
            title: "付款日期",
            width: 110,
            render: (_: unknown, row: Fee) => context.latestTransaction(row)?.transaction_date || "—",
        },
        {
            title: "申请人",
            width: 90,
            render: (_: unknown, row: Fee) => context.financePersonDisplayName(row.data.applicant || row.owner, row.data.applicant_display_name || (row as any).owner_display_name),
        },
    ];
}
