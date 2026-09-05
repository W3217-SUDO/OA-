import { Button, Tag } from "antd";
import { money } from "../constants";
import type { Reconciliation } from "../types";
export function createReconcileColumns(context: {
    readonly financePersonDisplayName: (identity: unknown, displayName?: unknown) => string;
    readonly confirmReconciliation: (row: Reconciliation) => Promise<void>;
}) {
    return [
        {
            title: "周期",
            dataIndex: "period_type",
            width: 90,
            render: (v: string) => <Tag color="blue">{v}</Tag>,
        },
        { title: "开始日期", dataIndex: "date_from", width: 110 },
        { title: "结束日期", dataIndex: "date_to", width: 110 },
        { title: "流水笔数", dataIndex: "transaction_count", width: 90 },
        { title: "流水金额", dataIndex: "total_amount", width: 140, render: money },
        {
            title: "差异金额",
            dataIndex: "discrepancy_amount",
            width: 130,
            render: (v: number) => (<span className={v ? "money-due" : ""}>{money(v)}</span>),
        },
        {
            title: "状态",
            dataIndex: "status",
            width: 90,
            render: (v: string) => (<Tag color={v === "已确认" ? "green" : "orange"}>{v}</Tag>),
        },
        { title: "操作人", dataIndex: "operator", width: 90, render: (value: string, row: Reconciliation) => context.financePersonDisplayName(value, (row as any).operator_display_name) },
        { title: "备注", dataIndex: "remark" },
        {
            title: "操作",
            key: "action",
            width: 90,
            render: (_: unknown, r: Reconciliation) => r.status === "待确认" ? (<Button type="link" onClick={() => context.confirmReconciliation(r)}>
            确认对账
          </Button>) : ("—"),
        },
    ];
}
