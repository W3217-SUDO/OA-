import { PaperClipOutlined } from "@ant-design/icons";
import { Button, Space, Tag } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import type { ConfigUpdate } from "antd/es/modal/confirm";
import dayjs from "dayjs";
import { money, statusColors } from "../constants";
import type { Fee, FinanceFlow } from "../types";
export function createInvoiceColumns(context: {
    readonly openCustomerDetail: (customer: unknown, customerNo?: unknown) => Promise<void>;
    readonly openCaseDetail: (caseNo: unknown) => Promise<void>;
    readonly openRecordFiles: (row: Fee, category: string, targets?: Fee[]) => Promise<void>;
    readonly openInvoiceDetail: (row: Fee) => Promise<void>;
    readonly submitFlow: (kind: "invoices" | "refunds", row: Fee) => Promise<void>;
    readonly canApprove: boolean;
    readonly reviewFlow: (kind: "invoices" | "refunds", row: Fee, approved: boolean) => {
        destroy: () => void;
        update: (configUpdate: ConfigUpdate) => void;
    };
    readonly canManage: boolean;
    readonly issueForm: FormInstance<any>;
    readonly setIssueTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly setVoidTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
}) {
    return [
        { title: "申请编号", dataIndex: "serial_no", width: 180 },
        { title: "客户", dataIndex: "customer", width: 190, render: (value: string, r: FinanceFlow) => value ? <Button type="link" onClick={() => context.openCustomerDetail(value, r.data.customer_no)}>{value}</Button> : "—" },
        {
            title: "案号",
            key: "case_no",
            width: 150,
            render: (_: unknown, r: FinanceFlow) => r.data.case_no ? <Button type="link" onClick={() => context.openCaseDetail(r.data.case_no)}>{r.data.case_no}</Button> : "—",
        },
        {
            title: "发票抬头",
            key: "title",
            width: 210,
            render: (_: unknown, r: FinanceFlow) => r.data.invoice_title || "—",
        },
        {
            title: "发票类型",
            key: "type",
            width: 130,
            render: (_: unknown, r: FinanceFlow) => r.data.invoice_type,
        },
        {
            title: "金额",
            key: "amount",
            width: 125,
            render: (_: unknown, r: FinanceFlow) => r.data.amount == null ? "无权限" : money(r.data.amount),
        },
        {
            title: "交付",
            key: "delivery",
            width: 100,
            render: (_: unknown, r: FinanceFlow) => r.data.delivery_method,
        },
        {
            title: "状态",
            dataIndex: "status",
            width: 95,
            render: (v: string) => (<Tag color={statusColors[v] || "default"}>{v}</Tag>),
        },
        {
            title: "发票号码",
            key: "invoice_no",
            width: 150,
            render: (_: unknown, r: FinanceFlow) => r.data.invoice_no || "—",
        },
        {
            title: "扫描件",
            key: "files",
            width: 95,
            render: (_: unknown, r: FinanceFlow) => (<Button type="link" icon={<PaperClipOutlined />} onClick={() => context.openRecordFiles(r, "发票扫描件")}>
          凭证
        </Button>),
        },
        {
            title: "操作",
            key: "action",
            fixed: "right" as const,
            width: 205,
            render: (_: unknown, r: FinanceFlow) => (<Space wrap>
          <Button type="link" onClick={() => void context.openInvoiceDetail(r)}>
            详情
          </Button>
          {["草稿", "已驳回"].includes(r.status) && (<Button type="link" onClick={() => context.submitFlow("invoices", r)}>
              提交
            </Button>)}
          {context.canApprove && r.status === "待审批" && (<>
              <Button type="link" onClick={() => context.reviewFlow("invoices", r, true)}>
                通过
              </Button>
              <Button type="link" danger onClick={() => context.reviewFlow("invoices", r, false)}>
                驳回
              </Button>
            </>)}
          {context.canManage && r.status === "待开票" && (<Button type="link" onClick={() => {
                        context.issueForm.setFieldsValue({ invoice_date: dayjs() });
                        context.setIssueTarget(r);
                    }}>
              登记开票
            </Button>)}
          {context.canManage && r.status === "已开票" && (<Button type="link" danger onClick={() => context.setVoidTarget(r)}>
              作废
            </Button>)}
        </Space>),
        },
    ];
}
