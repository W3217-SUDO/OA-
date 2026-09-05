import { Button } from "antd";
import { money } from "../constants";
import type { Fee, Transaction } from "../types";
export function createPaymentOriginalColumns(context: {
    readonly originalOperation: (_: unknown, row: Fee) => React.JSX.Element;
    readonly paymentStatus: (fee: Fee) => any;
    readonly openCaseDetail: (caseNo: unknown) => Promise<void>;
    readonly openContractDetail: (contractNo: unknown) => Promise<void>;
    readonly latestTransaction: (fee: Fee) => Transaction;
    readonly financePersonDisplayName: (identity: unknown, displayName?: unknown) => string;
}) {
    return [
        {
            title: "操作",
            key: "action",
            fixed: "left" as const,
            width: 150,
            render: context.originalOperation,
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
            title: "申请金额",
            width: 115,
            render: (_: unknown, row: Fee) => row.data.amount == null ? "—" : money(row.data.amount),
        },
        {
            title: "截止日期",
            width: 110,
            render: (_: unknown, row: Fee) => row.data.deadline || row.data.due_date || "—",
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
        {
            title: "合同编号",
            width: 145,
            render: (_: unknown, row: Fee) => row.data.contract_no ? <Button type="link" onClick={() => context.openContractDetail(row.data.contract_no)}>{row.data.contract_no}</Button> : "—",
        },
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
        {
            title: "客户管理人",
            width: 100,
            render: (_: unknown, row: Fee) => context.financePersonDisplayName(row.data.customer_manager, row.data.customer_manager_display_name),
        },
        {
            title: "交款人",
            width: 90,
            render: (_: unknown, row: Fee) => row.data.payer || row.data.handler || "—",
        },
    ];
}
