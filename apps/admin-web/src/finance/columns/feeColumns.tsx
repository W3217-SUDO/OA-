import { AuditOutlined, CheckCircleOutlined, DollarOutlined } from "@ant-design/icons";
import { Button, Space, Tag } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import dayjs from "dayjs";
import { money, statusColors } from "../constants";
import type { Fee } from "../types";
export function createFeeColumns(context: {
    readonly openCustomerDetail: (customer: unknown, customerNo?: unknown) => Promise<void>;
    readonly openCaseDetail: (caseNo: unknown) => Promise<void>;
    readonly feeAction: (row: Fee, type: "submit" | "approve") => Promise<void>;
    readonly canApprove: boolean;
    readonly transactionForm: FormInstance<any>;
    readonly setTransactionOpen: React.Dispatch<React.SetStateAction<boolean>>;
}) {
    return [
        { title: "费用编号", dataIndex: "serial_no", width: 175 },
        { title: "费用名称", dataIndex: "title", width: 240 },
        {
            title: "费用类型",
            key: "type",
            width: 100,
            render: (_: unknown, r: Fee) => (<Tag color="blue">{r.data.fee_type || "官方费用"}</Tag>),
        },
        {
            title: "金额",
            key: "amount",
            width: 120,
            render: (_: unknown, r: Fee) => (<b>{r.data.amount == null ? "无权限" : money(r.data.amount)}</b>),
        },
        { title: "客户", dataIndex: "customer", width: 180, render: (value: string, r: Fee) => value ? <Button type="link" onClick={() => context.openCustomerDetail(value, r.data.customer_no)}>{value}</Button> : "—" },
        {
            title: "案号",
            key: "case",
            width: 145,
            render: (_: unknown, r: Fee) => r.data.case_no ? <Button type="link" onClick={() => context.openCaseDetail(r.data.case_no)}>{r.data.case_no}</Button> : "—",
        },
        {
            title: "法院/机构",
            key: "court",
            width: 180,
            render: (_: unknown, r: Fee) => r.data.court || "—",
        },
        { title: "经办人", dataIndex: "owner", width: 90 },
        {
            title: "状态",
            dataIndex: "status",
            width: 90,
            render: (v: string) => (<Tag color={statusColors[v] || "default"}>{v}</Tag>),
        },
        {
            title: "操作",
            key: "action",
            fixed: "right" as const,
            width: 145,
            render: (_: unknown, r: Fee) => (<Space>
          {["草稿", "已退回"].includes(r.status) && (<Button type="link" icon={<AuditOutlined />} onClick={() => context.feeAction(r, "submit")}>
              提交
            </Button>)}
          {context.canApprove && r.status === "待审批" && (<Button type="link" icon={<CheckCircleOutlined />} onClick={() => context.feeAction(r, "approve")}>
              通过
            </Button>)}
          {r.data.amount != null &&
                    ["已审批", "部分付款"].includes(r.status) && (<Button type="link" icon={<DollarOutlined />} onClick={() => {
                        context.transactionForm.setFieldsValue({
                            finance_record_id: r.id,
                            transaction_type: "付款",
                            transaction_date: dayjs(),
                            counterparty: r.data.payee || r.customer,
                        });
                        context.setTransactionOpen(true);
                    }}>
                付款
              </Button>)}
        </Space>),
        },
    ];
}
