import { Modal, Descriptions, Button, Tag } from "antd";
import type { Row } from "./types";

interface LinkedCaseModalProps {
  open: boolean;
  linkedCase: Row | null;
  projectedPersonDisplayName: (displayName: unknown, username: unknown) => string;
  onClose: () => void;
}

export default function LinkedCaseModal({
  open,
  linkedCase,
  projectedPersonDisplayName,
  onClose,
}: LinkedCaseModalProps) {
  return (
    <Modal
      width={760}
      open={open}
      title={`关联案件：${linkedCase?.serial_no || ""}`}
      footer={<Button onClick={onClose}>关闭</Button>}
      onCancel={onClose}
    >
      <Descriptions
        bordered
        size="small"
        column={2}
        items={
          linkedCase
            ? [
                { key: "no", label: "案号", children: linkedCase.serial_no },
                {
                  key: "status",
                  label: "阶段",
                  children: <Tag color="blue">{linkedCase.status}</Tag>,
                },
                {
                  key: "title",
                  label: "案件名称",
                  children: linkedCase.title,
                  span: 2,
                },
                {
                  key: "customer",
                  label: "客户/原告",
                  children: linkedCase.customer,
                },
                {
                  key: "opponent",
                  label: "对方当事人",
                  children:
                    linkedCase.data.opponent ||
                    linkedCase.data.defendant ||
                    "—",
                },
                {
                  key: "court",
                  label: "法院",
                  children: linkedCase.data.court || "—",
                },
                {
                  key: "owner",
                  label: "负责人",
                  children: projectedPersonDisplayName(
                    linkedCase.owner_display_name,
                    linkedCase.owner,
                  ),
                },
                {
                  key: "description",
                  label: "说明",
                  children: linkedCase.description || "—",
                  span: 2,
                },
              ]
            : []
        }
      />
    </Modal>
  );
}
