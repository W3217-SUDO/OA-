import { Button, Dropdown, Space } from "antd";

type FinanceFeeQueryActionsProps = {
  exportLoading: boolean;
  actionLoading: boolean;
  onExport: (selected: boolean) => void | Promise<void>;
  onMoreAction: (key: string) => void | Promise<void>;
};

export function FinanceFeeQueryActions({ exportLoading, actionLoading, onExport, onMoreAction }: FinanceFeeQueryActionsProps) {
  return <Space size={7}>
    <Dropdown
      trigger={["click"]}
      menu={{
        items: [
          { key: "selected", label: "导出选中" },
          { key: "all", label: "导出全部" },
        ],
        onClick: ({ key }) => void onExport(key === "selected"),
      }}
    >
      <Button loading={exportLoading}>导出 ▾</Button>
    </Dropdown>
    <Dropdown
      trigger={["click"]}
      menu={{
        items: [
          { key: "upload", label: "上传案件文档" },
          { key: "official-fee", label: "新增案件费用" },
          { key: "internal-fee", label: "新增内部费用" },
          { key: "batch-modify", label: "批量修改" },
          { key: "authorization", label: "生成授权委托书" },
          { key: "law-firm-letter", label: "生成律所函" },
          { key: "identity", label: "生成身份证明" },
          { key: "settlement", label: "生成结算提成表" },
          { key: "tasks", label: "案件任务" },
          { key: "logs", label: "案件日志" },
        ],
        onClick: ({ key }) => onMoreAction(key),
      }}
    >
      <Button loading={actionLoading}>更多操作 ▾</Button>
    </Dropdown>
  </Space>;
}
