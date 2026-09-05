import { Button, Modal, Table } from "antd";
import dayjs from "dayjs";
import type { SealAuditRow } from "../sealWorkflowPolicy";

interface SealAuditListModalProps {
  open: boolean;
  rows: SealAuditRow[];
  onClose: () => void;
}

export function SealAuditListModal({
  open,
  rows,
  onClose,
}: SealAuditListModalProps) {
  return (
    <Modal
      open={open}
      title="审批流程"
      footer={<Button onClick={onClose}>关闭</Button>}
      onCancel={onClose}
    >
      <Table
        size="small"
        rowKey="id"
        pagination={false}
        locale={{ emptyText: "" }}
        dataSource={rows}
        columns={[
          { title: "审批人", dataIndex: "auditor" },
          { title: "审核状态", dataIndex: "audit_status" },
          {
            title: "审核日期",
            dataIndex: "audit_date",
            render: (value: string) => dayjs(value).format("YYYY-MM-DD"),
          },
          { title: "审批意见", dataIndex: "audit_content" },
          {
            title: "审批轮次",
            dataIndex: "audit_round",
          },
          { title: "当前步骤", dataIndex: "current_step" },
        ]}
      />
    </Modal>
  );
}
