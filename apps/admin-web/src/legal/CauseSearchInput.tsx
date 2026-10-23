import { AutoComplete } from "antd";
import { useMemo, useState } from "react";

/**
 * 案由/罪名关键词搜索控件（10.22 第9、10行）。
 *
 * - 数据源与民事新建相同：`/cases/reference-options` 返回的启用案由字典（causeOptions）。
 * - 旧系统刑事“罪名”是输入框 + 联想：输入“抢劫”出现“抢劫罪”等候选；这里沿用该形态，
 *   允许保存字典外文本，保证历史手填罪名打开即回显、不改也能直接保存。
 * - 值始终是字符串，与 `data.cause_or_charge` 及后端 `cause_or_charge` 自由文本口径一致。
 */
export interface CauseOption {
  value: string;
  label: string;
}

interface CauseSearchInputProps {
  value?: string;
  onChange?: (value: string) => void;
  options: CauseOption[];
  placeholder?: string;
  disabled?: boolean;
  /** 下拉最多显示的候选数，避免全量字典一次渲染。 */
  limit?: number;
}

export const CAUSE_SEARCH_LIMIT = 100;

export function filterCauseOptions(options: CauseOption[], keyword: string, limit = CAUSE_SEARCH_LIMIT): CauseOption[] {
  const text = String(keyword || "").trim().toLowerCase();
  const seen = new Set<string>();
  const matched: CauseOption[] = [];
  for (const option of options) {
    const label = String(option.label || option.value || "");
    const value = String(option.value || label);
    if (!value || seen.has(value)) continue;
    if (text && !label.toLowerCase().includes(text) && !value.toLowerCase().includes(text)) continue;
    seen.add(value);
    matched.push({ value, label });
    if (matched.length >= limit) break;
  }
  return matched;
}

export function CauseSearchInput({ value, onChange, options, placeholder, disabled, limit = CAUSE_SEARCH_LIMIT }: CauseSearchInputProps) {
  const [keyword, setKeyword] = useState<string | null>(null);
  const filtered = useMemo(() => filterCauseOptions(options, keyword ?? "", limit), [options, keyword, limit]);
  return (
    <AutoComplete
      value={value ?? ""}
      options={filtered}
      disabled={disabled}
      allowClear
      placeholder={placeholder}
      popupMatchSelectWidth
      notFoundContent={keyword ? "字典中无匹配案由，可直接保存输入内容" : null}
      onSearch={(text) => setKeyword(text)}
      onFocus={() => setKeyword(String(value ?? ""))}
      onChange={(next) => onChange?.(String(next ?? ""))}
      onSelect={(next) => { setKeyword(String(next ?? "")); onChange?.(String(next ?? "")); }}
      onBlur={() => { const trimmed = String(value ?? "").trim(); if (trimmed !== (value ?? "")) onChange?.(trimmed); }}
      style={{ width: "100%" }}
      data-testid="cause-search-input"
    />
  );
}
