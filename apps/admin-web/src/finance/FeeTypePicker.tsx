import { useEffect, useState } from "react";
import { TreeSelect, message } from "antd";
import { api } from "../api";

export type FeeTypeOption = {
  id: number; code: string; name: string; parent_code: string;
  base_fee_type: string; selectable: boolean; expense_scopes: string[];
};

export function buildFeeTypeTree(items: FeeTypeOption[], editing = false, scope?: string) {
  const byCode = new Map(items.map(item => [item.code, item]));
  const build = (parent: string, seen = new Set<string>()): any[] => items
    .filter(item => (byCode.has(item.parent_code) ? item.parent_code : "") === parent && !seen.has(item.code))
    .map(item => {
      const children = build(item.code, new Set([...seen, item.code]));
      return {
        key: item.code, value: editing ? item.id : item.code, title: item.name,
        selectable: editing && item.selectable && (!scope || item.expense_scopes.includes(scope)),
        disabled: !children.length && (editing ? !item.selectable || Boolean(scope && !item.expense_scopes.includes(scope)) : item.code.startsWith("-") || item.name.startsWith("请选择")),
        children: children.length ? children : undefined,
      };
    });
  return build("");
}

// Every business picker reads the same authoritative catalog, including roots.
// Filters expand a branch to its leaf names; editing persists the leaf's id.
export function FeeTypePicker({ value, onChange, onSelectOption, multiple = false, editing = false, scope, disabled = false }: {
  value?: any; onChange?: (value: any) => void;
  onSelectOption?: (item: FeeTypeOption) => void;
  multiple?: boolean; editing?: boolean; scope?: string; disabled?: boolean;
}) {
  const [items, setItems] = useState<FeeTypeOption[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    setLoading(true);
    api.get("/system/parameters/options", { params: { category: "fee_type" } })
      .then(({ data }) => { if (active) setItems(data.items || []); })
      .catch(() => { if (active) message.error("费用类型加载失败，请重新打开页面重试"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  const byCode = new Map(items.map(item => [item.code, item]));
  return <TreeSelect allowClear showSearch treeNodeFilterProp="title" style={{ width: "100%" }}
    placeholder="请选择费用类型" loading={loading} disabled={disabled} value={editing ? value : items.filter(item => (Array.isArray(value) ? value : [value]).includes(item.name)).map(item => item.code)}
    treeData={buildFeeTypeTree(items, editing, scope)} treeCheckable={multiple} showCheckedStrategy={TreeSelect.SHOW_ALL} maxTagCount="responsive"
    onChange={next => {
      onChange?.(editing ? next : (Array.isArray(next) ? next : next ? [next] : []).map(code => byCode.get(String(code))?.name).filter(Boolean));
      const selected = items.find(item => item.id === next);
      if (selected) onSelectOption?.(selected);
    }} />;
}
