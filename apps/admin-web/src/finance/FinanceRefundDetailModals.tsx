import { Button, Descriptions, Modal, Select, Tag } from "antd";
import { money, statusColors } from "./constants";
import type { FinanceFlow } from "./types";

export interface RefundDetailModalProps {
  refund: FinanceFlow | null;
  onClose: () => void;
  onOpenCase: (caseNo: unknown) => void;
  onOpenCustomer: (customer: string, customerNo?: string) => void;
  financePersonDisplayName: (identity?: unknown, displayName?: unknown) => string;
}

export function RefundDetailModal({
  refund: refundDetail,
  onClose,
  onOpenCase: openCaseDetail,
  onOpenCustomer: openCustomerDetail,
  financePersonDisplayName,
}: RefundDetailModalProps) {
  return (
      <Modal
        width={760}
        open={Boolean(refundDetail)}
        title={`退款申请详情：${refundDetail?.serial_no || ""}`}
        footer={null}
        onCancel={onClose}
      >
        {refundDetail && (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="退款申请号">{refundDetail.serial_no || "—"}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={statusColors[refundDetail.status] || "default"}>{refundDetail.status || "—"}</Tag></Descriptions.Item>
            <Descriptions.Item label="关联案号">{refundDetail.data.case_no ? <Button type="link" onClick={() => openCaseDetail(refundDetail.data.case_no)}>{refundDetail.data.case_no}</Button> : "—"}</Descriptions.Item>
            <Descriptions.Item label="客户">{refundDetail.customer ? <Button type="link" onClick={() => openCustomerDetail(refundDetail.customer, refundDetail.data.customer_no)}>{refundDetail.customer}</Button> : "—"}</Descriptions.Item>
            <Descriptions.Item label="退款金额">{refundDetail.data.amount == null ? "—" : money(refundDetail.data.amount)}</Descriptions.Item>
            <Descriptions.Item label="预计到账">{refundDetail.data.expected_date || "—"}</Descriptions.Item>
            <Descriptions.Item label="原缴费票号">{refundDetail.data.original_payment_no || "—"}</Descriptions.Item>
            <Descriptions.Item label="退款账户">{refundDetail.data.refund_account_name || "—"}</Descriptions.Item>
            <Descriptions.Item label="实际到账">{refundDetail.data.actual_date || "—"}</Descriptions.Item>
            <Descriptions.Item label="退款凭证号">{refundDetail.data.voucher_no || "—"}</Descriptions.Item>
            <Descriptions.Item label="申请人">{financePersonDisplayName(refundDetail.data.applicant || refundDetail.owner, refundDetail.data.applicant_display_name || refundDetail.data.owner_display_name)}</Descriptions.Item>
            <Descriptions.Item label="说明" span={2}>{refundDetail.description || refundDetail.data.remark || "—"}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
  );
}

export interface RefundBatchStatusModalProps {
  open: boolean;
  selectedCount: number;
  status: string;
  loading: boolean;
  onStatusChange: (status: string) => void;
  onSubmit: () => Promise<void>;
  onClose: () => void;
}

export function RefundBatchStatusModal({
  open: refundBatchStatusOpen,
  selectedCount,
  status: refundBatchStatus,
  loading: refundMutationLoading,
  onStatusChange: setRefundBatchStatus,
  onSubmit: updateRefundBatchStatus,
  onClose,
}: RefundBatchStatusModalProps) {
  return (
      <Modal
        open={refundBatchStatusOpen}
        title={`退费进度修改（已选 ${selectedCount} 条）`}
        okText="确定"
        cancelText="取消"
        confirmLoading={refundMutationLoading}
        onOk={updateRefundBatchStatus}
        onCancel={onClose}
      >
        <Select
          aria-label="批量退费进度"
          value={refundBatchStatus}
          onChange={setRefundBatchStatus}
          options={["待审批", "退款办理中", "已驳回"].map((value) => ({
            value,
            label: value,
          }))}
          style={{ width: "100%" }}
        />
      </Modal>
  );
}
