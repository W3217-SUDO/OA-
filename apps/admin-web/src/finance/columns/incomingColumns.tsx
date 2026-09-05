import { Tag } from "antd";
import { money } from "../constants";
import type { IncomingPayment } from "../types";
export function createIncomingColumns(context: {
    readonly financePersonDisplayName: (identity: unknown, displayName?: unknown) => string;
    readonly originalIncomingOperation: (_: unknown, r: IncomingPayment) => React.JSX.Element;
}) {
    return [
        { title: "到账编号", dataIndex: "receipt_no", width: 180 },
        { title: "到账日期", dataIndex: "received_date", width: 110 },
        { title: "付款单位/户名", dataIndex: "payer_name", width: 210 },
        { title: "银行流水号", dataIndex: "bank_reference", width: 165 },
        {
            title: "到账金额",
            dataIndex: "amount",
            width: 130,
            render: (v: number | null) => (v == null ? "无权限" : money(v)),
        },
        {
            title: "已分配",
            dataIndex: "allocated_amount",
            width: 120,
            render: (v: number | null) => (v == null ? "无权限" : money(v)),
        },
        {
            title: "认领客户",
            dataIndex: "claimed_customer",
            width: 190,
            render: (v: string) => v || "—",
        },
        {
            title: "状态",
            dataIndex: "status",
            width: 100,
            render: (v: string) => (<Tag color={v === "已分配" ? "green" : v === "待认领" ? "orange" : "blue"}>
          {v}
        </Tag>),
        },
        {
            title: "认领人",
            dataIndex: "claimant",
            width: 90,
            render: (v: string, row: IncomingPayment) => context.financePersonDisplayName(v, (row as any).claimant_display_name),
        },
        { title: "备注", dataIndex: "remark", ellipsis: true },
        {
            title: "操作",
            key: "action",
            fixed: "right" as const,
            width: 205,
            render: context.originalIncomingOperation,
        },
    ];
}
