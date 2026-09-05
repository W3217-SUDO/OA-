import { PaperClipOutlined } from "@ant-design/icons";
import { Button, Space, Tag } from "antd";
import type { FormInstance } from "antd/es/form/hooks/useForm";
import type { ConfigUpdate } from "antd/es/modal/confirm";
import dayjs from "dayjs";
import { money, statusColors } from "../constants";
import type { Fee, FinanceFlow } from "../types";
export function createRefundColumns(context: {
    readonly openCaseDetail: (caseNo: unknown) => Promise<void>;
    readonly openCustomerDetail: (customer: unknown, customerNo?: unknown) => Promise<void>;
    readonly openRecordFiles: (row: Fee, category: string, targets?: Fee[]) => Promise<void>;
    readonly openRefundDetail: (row: Fee) => Promise<void>;
    readonly refundAmountForm: FormInstance<any>;
    readonly setRefundAmountTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
    readonly submitFlow: (kind: "invoices" | "refunds", row: Fee) => Promise<void>;
    readonly canApprove: boolean;
    readonly reviewFlow: (kind: "invoices" | "refunds", row: Fee, approved: boolean) => {
        destroy: () => void;
        update: (configUpdate: ConfigUpdate) => void;
    };
    readonly canManage: boolean;
    readonly refundCompleteForm: FormInstance<any>;
    readonly setRefundCompleteTarget: React.Dispatch<React.SetStateAction<Fee | null>>;
}) {
    return [
        { title: "申请编号", dataIndex: "serial_no", width: 180 },
        {
            title: "案号",
            key: "case_no",
            width: 150,
            render: (_: unknown, r: FinanceFlow) => r.data.case_no ? <Button type="link" onClick={() => context.openCaseDetail(r.data.case_no)}>{r.data.case_no}</Button> : "—",
        },
        { title: "客户", dataIndex: "customer", width: 180, render: (value: string, r: FinanceFlow) => value ? <Button type="link" onClick={() => context.openCustomerDetail(value, r.data.customer_no)}>{value}</Button> : "—" },
        {
            title: "法院",
            key: "court",
            width: 190,
            render: (_: unknown, r: FinanceFlow) => r.data.court,
        },
        {
            title: "原缴费票号",
            key: "payment_no",
            width: 150,
            render: (_: unknown, r: FinanceFlow) => r.data.original_payment_no,
        },
        {
            title: "退款金额",
            key: "amount",
            width: 125,
            render: (_: unknown, r: FinanceFlow) => r.data.amount == null ? "无权限" : money(r.data.amount),
        },
        {
            title: "退款账户",
            key: "account",
            width: 180,
            render: (_: unknown, r: FinanceFlow) => r.data.refund_account_name || "—",
        },
        {
            title: "预计到账",
            key: "expected",
            width: 110,
            render: (_: unknown, r: FinanceFlow) => r.data.expected_date || "—",
        },
        {
            title: "实际到账",
            key: "actual",
            width: 110,
            render: (_: unknown, r: FinanceFlow) => r.data.actual_date || "—",
        },
        {
            title: "退款凭证号",
            key: "voucher",
            width: 135,
            render: (_: unknown, r: FinanceFlow) => r.data.refund_voucher_no || r.data.voucher_no || "—",
        },
        {
            title: "状态",
            dataIndex: "status",
            width: 105,
            render: (v: string) => (<Tag color={statusColors[v] || "default"}>{v}</Tag>),
        },
        {
            title: "到账凭证",
            key: "files",
            width: 105,
            render: (_: unknown, r: FinanceFlow) => (<Button type="link" icon={<PaperClipOutlined />} onClick={() => context.openRecordFiles(r, "退费凭证")}>
          凭证
        </Button>),
        },
        {
            title: "操作",
            key: "action",
            fixed: "right" as const,
            width: 205,
            render: (_: unknown, r: FinanceFlow) => (<Space wrap>
          <Button type="link" onClick={() => void context.openRefundDetail(r)}>
            详情
          </Button>
          {['草稿', '已驳回'].includes(r.status) && (<Button type="link" onClick={() => {
                        context.refundAmountForm.setFieldsValue({
                            amount: r.data.amount,
                            comment: "",
                        });
                        context.setRefundAmountTarget(r);
                    }}>
              修改金额
            </Button>)}
          {["草稿", "已驳回"].includes(r.status) && (<Button type="link" onClick={() => context.submitFlow("refunds", r)}>
              提交
            </Button>)}
          {context.canApprove && r.status === "待审批" && (<>
              <Button type="link" onClick={() => context.reviewFlow("refunds", r, true)}>
                通过
              </Button>
              <Button type="link" danger onClick={() => context.reviewFlow("refunds", r, false)}>
                驳回
              </Button>
            </>)}
          {context.canManage && r.status === "退款办理中" && (<Button type="link" onClick={() => {
                        context.refundCompleteForm.setFieldsValue({ actual_date: dayjs() });
                        context.setRefundCompleteTarget(r);
                    }}>
              登记到账
            </Button>)}
        </Space>),
        },
    ];
}
