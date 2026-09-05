import { Button,Drawer,Input,Space,Table } from "antd";

interface FeeReviewDrawerProps {
  open: boolean;
  initialView: string;
  reviewComment: string;
  reviewLoading: boolean;
  paymentReviewRows: any[];
  feeReviewRows: any[];
  reviewNumber: (value: unknown) => React.ReactNode;
  onClose: () => void;
  onCommentChange: (value: string) => void;
  onSubmit: (approved: boolean) => void;
  onOpenCaseDetail: (caseNo: unknown) => void;
}

export function FeeReviewDrawer({
  open,
  initialView,
  reviewComment,
  reviewLoading,
  paymentReviewRows,
  feeReviewRows,
  reviewNumber,
  onClose,
  onCommentChange,
  onSubmit,
  onOpenCaseDetail,
}: FeeReviewDrawerProps) {
  const isPaymentAudit = initialView === "finance-payment-audit";

  const columns = isPaymentAudit
    ? [
        {
          title: "案号",
          dataIndex: "case_no",
          width: 100,
          render: (value: unknown) =>
            value ? (
              <Button type="link" onClick={() => onOpenCaseDetail(value)}>
                {String(value)}
              </Button>
            ) : (
              "—"
            ),
        },
        { title: "原告", dataIndex: "plaintiff", width: 100 },
        {
          title: "金额",
          dataIndex: "amount",
          width: 80,
          render: reviewNumber,
        },
        { title: "费用类型", dataIndex: "fee_type", width: 90 },
        { title: "付款备注", dataIndex: "payment_remark", width: 120 },
      ]
    : [
        {
          title: "案号",
          dataIndex: "case_no",
          width: 88,
          render: (value: unknown) =>
            value ? (
              <Button type="link" onClick={() => onOpenCaseDetail(value)}>
                {String(value)}
              </Button>
            ) : (
              "—"
            ),
        },
        {
          title: (
            <span className="finance-stacked-header">
              <span>提成</span>
              <span>类型</span>
            </span>
          ),
          dataIndex: "commission_type",
          width: 54,
          render: (value: unknown) => value || "—",
        },
        {
          title: (
            <span className="finance-stacked-header">
              <span>支付</span>
              <span>对象</span>
            </span>
          ),
          dataIndex: "payee",
          width: 54,
          render: (value: unknown) => value || "—",
        },
        {
          title: "基数",
          dataIndex: "base_amount",
          width: 54,
          render: reviewNumber,
        },
        {
          title: (
            <span className="finance-stacked-header">
              <span>基数</span>
              <span>提成</span>
            </span>
          ),
          dataIndex: "base_commission",
          width: 54,
          render: reviewNumber,
        },
        {
          title: (
            <span className="finance-stacked-header">
              <span>实际</span>
              <span>提成</span>
            </span>
          ),
          dataIndex: "actual_commission",
          width: 54,
          render: reviewNumber,
        },
        {
          title: (
            <span className="finance-stacked-header">
              <span>已付</span>
              <span>调查费</span>
            </span>
          ),
          dataIndex: "paid_investigation",
          width: 47,
          render: reviewNumber,
        },
        {
          title: (
            <span className="finance-stacked-header">
              <span>已付</span>
              <span>案源费</span>
            </span>
          ),
          dataIndex: "paid_source",
          width: 47,
          render: reviewNumber,
        },
        {
          title: (
            <span className="finance-stacked-header">
              <span>已付</span>
              <span>文书费</span>
            </span>
          ),
          dataIndex: "paid_document",
          width: 47,
          render: reviewNumber,
        },
        {
          title: (
            <span className="finance-stacked-header">
              <span>已付</span>
              <span>开庭费</span>
            </span>
          ),
          dataIndex: "paid_hearing",
          width: 47,
          render: reviewNumber,
        },
      ];

  const dataSource = (isPaymentAudit ? paymentReviewRows : feeReviewRows) as any;

  return (
    <Drawer
      open={open}
      title={
        <h5>{initialView === "finance-payment-audit" ? "付款审批" : "提成审批"}</h5>
      }
      width={580}
      placement="right"
      mask={false}
      closable={{ placement: "end" }}
      rootClassName="finance-review-drawer"
      onClose={onClose}
      footer={<Button onClick={onClose}>取消</Button>}
    >
      <Input.TextArea
        aria-label="审批意见"
        placeholder="审批意见"
        value={reviewComment}
        onChange={(event) => onCommentChange(event.target.value)}
        rows={2}
      />
      <Space className="finance-review-actions">
        <Button
          type="primary"
          loading={reviewLoading}
          onClick={() => onSubmit(true)}
        >
          同意
        </Button>
        <Button
          danger
          loading={reviewLoading}
          onClick={() => onSubmit(false)}
        >
          拒绝
        </Button>
      </Space>
      <Table
        rowKey="key"
        size="small"
        pagination={false}
        tableLayout="fixed"
        columns={columns}
        dataSource={dataSource}
      />
    </Drawer>
  );
}

export default FeeReviewDrawer;
