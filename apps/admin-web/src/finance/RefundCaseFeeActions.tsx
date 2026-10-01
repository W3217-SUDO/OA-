import { Button, Dropdown, Input, Modal, Select } from "antd";
import type { RefundCaseFeeLogKind } from "./types";

export interface RefundCaseFeeOperationMenuProps {
  requireSelection: () => number[];
  getSelectedStatus: () => string;
  onOpenStatus: (status: string) => void;
  onOpenLog: (kind: RefundCaseFeeLogKind) => void;
}

export interface RefundCaseFeeMarkButtonProps {
  loading: boolean;
  requireSelection: () => number[];
  onMarkNotRequired: () => Promise<void>;
}

export interface RefundCaseFeeModalsProps {
  selectedCount: number;
  loading: boolean;
  statusOpen: boolean;
  status: string;
  onStatusChange: (status: string) => void;
  onCloseStatus: () => void;
  onSubmitStatus: () => Promise<void>;
  logKind: RefundCaseFeeLogKind | null;
  logContent: string;
  onLogContentChange: (content: string) => void;
  onCloseLog: () => void;
  onSubmitLog: () => Promise<void>;
}

export function RefundCaseFeeOperationMenu({
  requireSelection,
  getSelectedStatus,
  onOpenStatus,
  onOpenLog,
}: RefundCaseFeeOperationMenuProps) {
  return (
    <Dropdown
      trigger={["click"]}
      menu={{
        items: [
          { key: "status", label: "退费进度修改" },
          { key: "court", label: "添加法院日志" },
          { key: "received", label: "添加到账日志" },
          { key: "other", label: "添加其他日志" },
        ],
        onClick: ({ key }) => {
          if (!requireSelection().length) return;
          if (key === "status") {
            onOpenStatus(getSelectedStatus());
          } else if (key === "court" || key === "received" || key === "other") {
            onOpenLog(key);
          }
        },
      }}
    >
      <Button>退费操作 ▾</Button>
    </Dropdown>
  );
}

export function RefundCaseFeeMarkButton({
  loading,
  requireSelection,
  onMarkNotRequired,
}: RefundCaseFeeMarkButtonProps) {
  return (
    <Button
      danger
      loading={loading}
      onClick={() => {
        if (!requireSelection().length) return;
        Modal.confirm({
          title: "标记不再办理退费",
          content: "确认将选中费用移出待退费列表？",
          okText: "确认标记",
          cancelText: "取消",
          onOk: onMarkNotRequired,
        });
      }}
    >
      标记不再办理退费
    </Button>
  );
}

export function RefundCaseFeeModals({
  selectedCount,
  loading,
  statusOpen,
  status,
  onStatusChange,
  onCloseStatus,
  onSubmitStatus,
  logKind,
  logContent,
  onLogContentChange,
  onCloseLog,
  onSubmitLog,
}: RefundCaseFeeModalsProps) {
  return (
    <>
      <Modal
        open={statusOpen}
        title={`退费进度修改（已选 ${selectedCount} 条）`}
        okText="确定"
        cancelText="取消"
        confirmLoading={loading}
        onOk={() => void onSubmitStatus()}
        onCancel={onCloseStatus}
      >
        <Select
          aria-label="案件费用退费进度"
          value={status}
          onChange={onStatusChange}
          options={[
            ["R10", "准备材料"],
            ["R20", "客户盖章"],
            ["R30", "已提交法院"],
            ["R35", "待法院现场办理"],
            ["R40", "退费到客户"],
            ["R50", "回款待分配"],
          ].map(([value, label]) => ({ value, label }))}
          style={{ width: "100%" }}
        />
      </Modal>
      <Modal
        open={Boolean(logKind)}
        title={{ court: "添加法院日志", received: "添加到账日志", other: "添加其他日志" }[logKind || "other"]}
        okText="保存"
        cancelText="取消"
        confirmLoading={loading}
        onOk={() => void onSubmitLog()}
        onCancel={onCloseLog}
      >
        <Input.TextArea
          aria-label="退费日志内容"
          rows={4}
          value={logContent}
          onChange={(event) => onLogContentChange(event.target.value)}
          placeholder="请输入日志内容"
        />
      </Modal>
    </>
  );
}
