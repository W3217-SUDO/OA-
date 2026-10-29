import { DownOutlined } from "@ant-design/icons";
import { Button, Dropdown } from "antd";
import type { MenuProps } from "antd";
import type { CaseDetailCapabilities } from "./types";

type Props = {
  selected: boolean;
  capabilities: CaseDetailCapabilities;
  canAssignTeam: boolean;
  canChangePhase: boolean;
  onAction: (key: string) => void;
};

export function CaseOperationsMenu({ selected, capabilities, canAssignTeam, canChangePhase, onAction }: Props) {
  const batchItems: MenuProps["items"] = [
    ...(canAssignTeam ? [
      { key: "batch-hearing-lawyer", label: "修改开庭律师" },
      { key: "batch-handling-lawyer", label: "修改经办律师" },
      { key: "batch-assistant", label: "修改律师助理" },
    ] : []),
    ...(canChangePhase ? [{ key: "batch-stage", label: "修改案件阶段" }] : []),
  ];
  const items: MenuProps["items"] = selected ? [
    { key: "upload-document", label: "上传案件文档", disabled: !capabilities.can_upload_attachment },
    ...(capabilities.can_create_finance ? [
      ...(["firm", "platform"] as const).map((scope) => ({
        key: `${scope}-fees`, label: scope === "firm" ? "新增律所费用" : "新增平台费用",
        children: ["官费", "第三方费用", "代理费", "其他费用"].map((kind) => ({ key: `${scope}-${kind}`, label: `新增${kind}` })),
      })),
    ] : []),
    // BUG20261028012：内部结算单独授权。
    ...(capabilities.can_create_internal_fee ? [{ key: "internal-fee", label: "新增内部费用" }] : []),
    ...(batchItems.length ? [{ key: "batch-update", label: "批量修改", children: batchItems }] : []),
    ...(capabilities.can_generate_document ? [
      { key: "document-authorization-letter", label: "生成授权委托书" },
      { key: "document-law-firm-letter", label: "生成律所函" },
      { key: "document-identity-certificate", label: "生成身份证明" },
      { key: "document-settlement-list", label: "生成结算提成表" },
    ] : []),
    // 未配置该功能的旧接口数据（字段缺失）按可见处理，只有角色明确取消时才隐藏。
    ...(capabilities.can_view_case_tasks !== false ? [{ key: "case-tasks", label: "案件任务" }] : []),
    ...(capabilities.can_view_case_logs !== false ? [{ key: "case-logs", label: "案件日志" }] : []),
    ...(capabilities.can_export_print_table !== false ? [{ key: "export-print-table", label: "导出案件打印表" }] : []),
  ] : [{ key: "select", label: "请先选择案件", disabled: true }];

  return <Dropdown trigger={["click"]} menu={{
    items,
    onClick: ({ key }) => onAction(key),
    style: { maxHeight: "70vh", maxWidth: "calc(100vw - 24px)", overflowY: "auto" },
    styles: {
      item: { minHeight: 44 },
      itemContent: { whiteSpace: "normal", overflowWrap: "anywhere" },
      subMenu: {
        itemTitle: { minHeight: 44 },
        itemContent: { whiteSpace: "normal", overflowWrap: "anywhere" },
        list: { maxHeight: "70vh", maxWidth: "calc(100vw - 24px)", overflowY: "auto" },
      },
    },
  }}>
    <Button aria-label="更多案件操作" style={{ minHeight: 44 }}>更多操作 <DownOutlined /></Button>
  </Dropdown>;
}
