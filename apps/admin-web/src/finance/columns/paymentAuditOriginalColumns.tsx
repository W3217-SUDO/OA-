import { Button } from "antd";
import { money } from "../constants";
import type { Fee } from "../types";
export function createPaymentAuditOriginalColumns(context: {
    readonly setFeeReviewTargets: React.Dispatch<React.SetStateAction<Fee[]>>;
    readonly financePersonDisplayName: (identity: unknown, displayName?: unknown) => string;
    readonly openCaseDetail: (caseNo: unknown) => Promise<void>;
    readonly openContractDetail: (contractNo: unknown) => Promise<void>;
    readonly paymentStatus: (fee: Fee) => any;
}) {
    return [
        {
            title: "请款单号",
            dataIndex: "serial_no",
            width: 165,
            render: (value: string, row: Fee) => (<Button type="link" onClick={() => context.setFeeReviewTargets([row])}>
          {value}
        </Button>),
        },
        {
            title: "类型",
            width: 95,
            render: (_: unknown, row: Fee) => row.data.fee_type || "—",
        },
        {
            title: "收款单位",
            width: 180,
            render: (_: unknown, row: Fee) => row.data.payee || "—",
        },
        {
            title: "申请人",
            width: 90,
            render: (_: unknown, row: Fee) => context.financePersonDisplayName(row.data.applicant || row.owner, row.data.applicant_display_name || (row as any).owner_display_name),
        },
        {
            title: "申请付款金额",
            width: 125,
            render: (_: unknown, row: Fee) => row.data.amount == null ? "—" : money(row.data.amount),
        },
        {
            title: "交款截止日期",
            width: 120,
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
            title: "合同名称",
            width: 190,
            render: (_: unknown, row: Fee) => row.data.contract_title || "—",
        },
        {
            title: "申请日期",
            width: 110,
            render: (_: unknown, row: Fee) => (row.data.application_date || row.created_at || "—").slice(0, 10),
        },
        {
            title: "状态",
            width: 95,
            render: (_: unknown, row: Fee) => context.paymentStatus(row),
        },
    ];
}
