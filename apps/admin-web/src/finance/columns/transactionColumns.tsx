import { PaperClipOutlined } from "@ant-design/icons";
import { Button, Tag } from "antd";
import { money } from "../constants";
import type { Transaction } from "../types";
export function createTransactionColumns(context: {
    readonly openVouchers: (row: Transaction) => void;
    readonly financePersonDisplayName: (identity: unknown, displayName?: unknown) => string;
    readonly role: any;
    readonly rollbackFinanceTransaction: (row: Transaction) => void;
}) {
    return [
        { title: "日期", dataIndex: "transaction_date", width: 105 },
        {
            title: "类型",
            dataIndex: "transaction_type",
            width: 80,
            render: (v: string) => (<Tag color={v === "付款" ? "green" : v === "退费" ? "red" : "blue"}>
          {v}
        </Tag>),
        },
        {
            title: "金额",
            dataIndex: "amount",
            width: 130,
            render: (v: number | null) => (v == null ? "无权限" : money(v)),
        },
        {
            title: "关联费用",
            dataIndex: "finance_no",
            width: 175,
            render: (v: string) => v || "独立流水",
        },
        { title: "费用名称", dataIndex: "finance_title", width: 230 },
        { title: "凭证/票号", dataIndex: "voucher_no", width: 150 },
        {
            title: "凭证附件",
            key: "vouchers",
            width: 150,
            render: (_: unknown, r: Transaction) => (<Button type="link" icon={<PaperClipOutlined />} onClick={() => context.openVouchers(r)}>
          {r.voucher_count ? `${r.voucher_count} 个附件` : "上传凭证"}
        </Button>),
        },
        { title: "对方单位", dataIndex: "counterparty", width: 190 },
        { title: "登记人", dataIndex: "operator", width: 90, render: (value: string, row: Transaction) => context.financePersonDisplayName(value, (row as any).operator_display_name) },
        { title: "备注", dataIndex: "remark" },
        ...(context.role === "admin"
            ? [
                {
                    title: "操作",
                    key: "action",
                    fixed: "right" as const,
                    width: 96,
                    render: (_: unknown, r: Transaction) => (<Button danger type="link" onClick={() => context.rollbackFinanceTransaction(r)}>
                回退
              </Button>),
                },
            ]
            : []),
    ];
}
