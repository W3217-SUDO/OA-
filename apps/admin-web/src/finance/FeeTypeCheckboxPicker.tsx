import { useState } from "react";
import { Button, Input, Popover, Tree } from "antd";
import { FolderOutlined } from "@ant-design/icons";
import type { FeeTypeOption } from "./FeeTypePicker";
import { buildFeeTypeTree } from "./feeTypeTree";
import "./FeeTypeCheckboxPicker.css";

export function FeeTypeCheckboxPicker({ items, value, onChange, disabled, loading }: {
  items: FeeTypeOption[]; value: unknown; onChange?: (value: string[]) => void;
  disabled: boolean; loading: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<string[]>([]);
  const selected = (Array.isArray(value) ? value : value ? [value] : []).map(String);
  const selectedCodes = new Set(selected);
  const labels = items.filter(item => selectedCodes.has(item.code)).map(item => item.name);
  const treeData = buildFeeTypeTree(items);
  const changeOpen = (next: boolean) => {
    if (next) {
      // 勾选仅写入草稿，确定后才回填筛选条件。
      setDraft(selected);
      setExpanded(items.filter(item => !item.parent_code && item.name === "官费").map(item => item.code));
    }
    setOpen(next);
  };
  const content = <div className="finance-fee-type-picker">
    <div className="finance-fee-type-picker-heading">从下列案件费用中选择</div>
    <div className="finance-fee-type-picker-tree">
      <Tree checkable selectable={false} showIcon icon={<FolderOutlined />}
        treeData={treeData} checkedKeys={draft} expandedKeys={expanded}
        onExpand={keys => setExpanded(keys.map(String))}
        onCheck={keys => setDraft((Array.isArray(keys) ? keys : keys.checked).map(String))} />
    </div>
    <div className="finance-fee-type-picker-actions">
      <Button type="primary" size="small" onClick={() => { onChange?.(draft); setOpen(false); }}>确定</Button>
      <Button size="small" onClick={() => setOpen(false)}>取消</Button>
    </div>
  </div>;
  return <Popover trigger="click" placement="bottomLeft" arrow={false} open={!disabled && open} onOpenChange={changeOpen} content={content}>
    <Input readOnly disabled={disabled || loading} placeholder={loading ? "正在加载费用类型" : "费用类型"}
      value={labels.join(",")} title={labels.join(",")} aria-label="费用类型" />
  </Popover>;
}
