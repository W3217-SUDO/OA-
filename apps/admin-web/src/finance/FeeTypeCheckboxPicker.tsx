import { useState } from "react";
import { Button, Checkbox, Input, Popover } from "antd";
import type { FeeTypeOption } from "./FeeTypePicker";

// 与旧系统请款单费用选择顺序一致；额外配置的具体费用保留在末尾。
const feeOrder = [
  "检索费", "一审诉讼费", "二审诉讼费", "再审诉讼费", "公证费", "调解金额",
  "判决金额", "保全费", "公告费", "担保费", "鉴定费", "执行费",
  "公证服务费", "律师代理费", "律师咨询费", "律师培训费", "律师见证费", "平台代理费",
  "律师代理费(退费)", "核定成本", "案源介绍费", "权利人赔偿款", "投资人分成", "其他费用",
  "产品购买费", "案源提成", "案源固定提成", "文书提成", "文书固定提成", "文书退费提成",
  "开庭提成", "开庭固定提成", "翻译费", "投资提成", "调查提成", "调查固定提成",
  "调档费", "品牌管理费", "品牌固定管理费", "手续服务费", "任务逾期扣款", "服务费(调查)",
  "服务费(开庭)", "服务费(案源)", "服务费(文书)", "服务费(品管)",
];

export function FeeTypeCheckboxPicker({ items, value, onChange, disabled, loading }: {
  items: FeeTypeOption[]; value: unknown; onChange?: (value: string[]) => void;
  disabled: boolean; loading: boolean;
}) {
  const [open, setOpen] = useState(false);
  const parents = new Set(items.map(item => item.parent_code));
  const groups = new Map<string, string[]>();
  for (const item of items) {
    if (!item.parent_code || parents.has(item.code) || item.code.startsWith("-") || item.name.startsWith("请选择")) continue;
    groups.set(item.name, [...(groups.get(item.name) || []), item.code]);
  }
  const names = [...feeOrder.filter(name => groups.has(name)), ...[...groups.keys()].filter(name => !feeOrder.includes(name))];
  const selected = new Set((Array.isArray(value) ? value : value ? [value] : []).map(String));
  const labels = names.filter(name => groups.get(name)!.some(code => selected.has(code)));
  const content = <div style={{ width: 650, maxWidth: "calc(100vw - 48px)" }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#639ee0", color: "white", padding: "4px 10px" }}>
      <span>从下列案件费用类型中选择</span>
      <Button size="small" onClick={() => onChange?.([])}>清空</Button>
    </div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "4px 8px", padding: 10, maxHeight: "65vh", overflowY: "auto" }}>
      {names.map(name => <Checkbox key={name} checked={groups.get(name)!.some(code => selected.has(code))}
        style={{ margin: 0, fontSize: 12 }} onChange={event => {
          const next = new Set(selected);
          for (const code of groups.get(name)!) event.target.checked ? next.add(code) : next.delete(code);
          onChange?.([...next]);
        }}>{name}</Checkbox>)}
    </div>
  </div>;
  return <Popover trigger="click" placement="bottomLeft" open={!disabled && open} onOpenChange={setOpen} content={content}>
    <Input readOnly disabled={disabled || loading} placeholder={loading ? "正在加载费用类型" : "请选择费用类型"}
      value={labels.join("、")} title={labels.join("、")} aria-label="费用类型" />
  </Popover>;
}
