import { Button } from "antd";
import { money } from "../constants";
import type { Fee, Transaction } from "../types";
export function createFeeQueryOriginalColumns(context: {
    readonly originalOperation: (_: unknown, row: Fee) => React.JSX.Element;
    readonly paymentStatus: (fee: Fee) => any;
    readonly latestTransaction: (fee: Fee) => Transaction;
    readonly openCaseDetail: (caseNo: unknown) => Promise<void>;
    readonly openContractDetail: (contractNo: unknown) => Promise<void>;
    readonly openCustomerDetail: (customer: unknown, customerNo?: unknown) => Promise<void>;
    readonly financePersonDisplayName: (identity: unknown, displayName?: unknown) => string;
}) {
    return [
        { title: "操作", key: "action", width: 145, render: context.originalOperation },
        { title: "费用编号", dataIndex: "serial_no", width: 165 },
        {
            title: "费用类型",
            width: 100,
            render: (_: unknown, row: Fee) => row.data.fee_type || "—",
        },
        {
            title: "状态",
            width: 95,
            render: (_: unknown, row: Fee) => context.paymentStatus(row),
        },
        { title: "费用名称", dataIndex: "title", width: 190 },
        {
            title: "申请金额",
            width: 110,
            render: (_: unknown, row: Fee) => row.data.amount == null ? "—" : money(row.data.amount),
        },
        {
            title: "付款金额",
            width: 110,
            render: (_: unknown, row: Fee) => context.latestTransaction(row)?.amount == null
                ? "—"
                : money(context.latestTransaction(row)!.amount!),
        },
        {
            title: "申请日期",
            width: 110,
            render: (_: unknown, row: Fee) => (row.data.application_date || row.created_at || "—").slice(0, 10),
        },
        {
            title: "付款日期",
            width: 110,
            render: (_: unknown, row: Fee) => context.latestTransaction(row)?.transaction_date || "—",
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
        { title: "客户名称", dataIndex: "customer", width: 180, render: (value: string, row: Fee) => value ? <Button type="link" onClick={() => context.openCustomerDetail(value, row.data.customer_no)}>{value}</Button> : "—" },
        {
            title: "申请人",
            width: 90,
            render: (_: unknown, row: Fee) => context.financePersonDisplayName(row.data.applicant || row.owner, row.data.applicant_display_name || (row as any).owner_display_name),
        },
        {
            title: "经办人",
            width: 90,
            render: (_: unknown, row: Fee) => context.financePersonDisplayName(row.data.handler || row.owner, row.data.handler_display_name || (row as any).owner_display_name),
        },
        {
            title: "收款单位",
            width: 180,
            render: (_: unknown, row: Fee) => row.data.payee || context.latestTransaction(row)?.counterparty || "—",
        },
        {
            title: "备注",
            width: 180,
            render: (_: unknown, row: Fee) => row.data.description || row.data.remark || "—",
        },
    ];
}
