import { useEffect, useState } from "react";
import { TreeSelect, message } from "antd";
import { api } from "../api";
import { FeeTypeCheckboxPicker } from "./FeeTypeCheckboxPicker";
import { buildFeeTypeTree } from "./feeTypeTree";
export { buildFeeTypeTree } from "./feeTypeTree";

export type FeeTypeOption = {
  id: number; code: string; name: string; parent_code: string; historical_names?: string[];
  base_fee_type: string; selectable: boolean; expense_scopes: string[]; is_active: boolean;
};

export type FeeTypeCatalogAlias = { id: number; code: string };
export type FeeTypeCatalog = { items: FeeTypeOption[]; aliases: Record<string, FeeTypeCatalogAlias> };

export function matchesFeeTypeSelection(value: unknown, catalog: FeeTypeCatalog, data: Record<string, unknown>) {
  const selectedCodes = new Set((Array.isArray(value) ? value : value ? [value] : []).map(String));
  if (!selectedCodes.size) return true;
  if (!catalog.items.length) return false;
  const childrenByParent = new Map<string, string[]>();
  const byCode = new Map(catalog.items.map(item => [item.code, item]));
  for (const item of catalog.items) childrenByParent.set(item.parent_code, [...(childrenByParent.get(item.parent_code) || []), item.code]);
  const expandedCodes = new Set(selectedCodes);
  const pending = [...selectedCodes];
  while (pending.length) {
    for (const childCode of childrenByParent.get(pending.pop()!) || []) {
      if (!expandedCodes.has(childCode)) { expandedCodes.add(childCode); pending.push(childCode); }
    }
  }
  const matchedItems = [...expandedCodes].map(code => byCode.get(code)).filter(Boolean) as FeeTypeOption[];
  const matchedIds = new Set(matchedItems.map(item => String(item.id)));
  const matchedNames = new Set(matchedItems.flatMap(item => [item.name, ...(item.historical_names || [])]));
  for (const code of selectedCodes) {
    const item = byCode.get(code);
    if (item && !item.parent_code && item.base_fee_type) matchedNames.add(item.base_fee_type);
  }
  for (const [aliasId, alias] of Object.entries(catalog.aliases)) {
    if (matchedIds.has(String(alias.id))) { matchedIds.add(aliasId); expandedCodes.add(alias.code); }
  }
  const stableCodes = [data.fee_type_code, data.legacy_fee_type_code].filter(Boolean).map(String);
  const stableId = String(data.fee_type_id || "");
  if (stableCodes.length || stableId) return stableCodes.some(code => expandedCodes.has(code)) || matchedIds.has(stableId);
  const detailedNames = [data.fee_type_name, data.expense_subtype, data.commission_type].filter(Boolean);
  return (detailedNames.length ? detailedNames : [data.fee_type]).some(name => matchedNames.has(String(name || "")));
}

// 所有业务选择器读取同一目录；筛选保留类型代码，编辑保存末级类型 ID。
export function FeeTypePicker({ value, onChange, onSelectOption, onCatalogLoaded, multiple = false, editing = false, scope, disabled = false }: {
  value?: any; onChange?: (value: any) => void;
  onSelectOption?: (item: FeeTypeOption) => void;
  onCatalogLoaded?: (catalog: FeeTypeCatalog) => void;
  multiple?: boolean; editing?: boolean; scope?: string; disabled?: boolean;
}) {
  const [items, setItems] = useState<FeeTypeOption[]>([]);
  const [aliases, setAliases] = useState<Record<string, FeeTypeCatalogAlias>>({});
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    setLoading(true);
    api.get("/system/parameters/options", { params: { category: "fee_type" } })
      .then(({ data }) => { if (active) { const catalog = { items: data.items, aliases: data.aliases };
        setItems(catalog.items); setAliases(catalog.aliases); onCatalogLoaded?.(catalog); } })
      .catch(() => { if (active) message.error("费用类型加载失败，请重新打开页面重试"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [editing]);
  if (multiple && !editing) return <FeeTypeCheckboxPicker items={items} value={value} onChange={onChange} disabled={disabled} loading={loading} />;
  return <TreeSelect allowClear showSearch treeNodeFilterProp="title" style={{ width: "100%" }}
    placeholder="请选择费用类型" loading={loading} disabled={disabled} value={editing ? aliases[String(value)]?.id || value : (Array.isArray(value) ? value : value ? [value] : [])}
    treeData={buildFeeTypeTree(items, editing, scope)} treeCheckable={multiple} showCheckedStrategy={TreeSelect.SHOW_ALL} maxTagCount="responsive"
    onChange={next => {
      onChange?.(editing ? next : (Array.isArray(next) ? next : next ? [next] : []).map(String));
      const selected = editing ? items.find(item => item.id === Number(next)) : undefined;
      if (selected) onSelectOption?.(selected);
    }} />;
}
