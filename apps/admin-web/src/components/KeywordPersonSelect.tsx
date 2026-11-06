import { useState } from "react";
import { Select } from "antd";
import type { SelectProps } from "antd";
import type { DefaultOptionType } from "antd/es/select";
import "./keyword-person-select.css";

// pinyin-helpers:start
// 501629（tgn 11-05）：选人框支持拼音首字母查找，例如 cyd 找到曹亚迪。
// 用浏览器自带的中文拼音排序（Intl.Collator）按声母分界字推出每个汉字的首字母，不引入拼音库、不改人员接口。
// 钉钉手机内核 Chrome 100 支持 Intl.Collator 中文拼音排序。
const INITIAL_LETTERS = "abcdefghjklmnopqrstwxyz";
const INITIAL_BOUNDARIES = "阿八嚓哒妸发旮哈讥咔垃妈拏噢妑七呥扨它穵夕丫帀";
// 多音字在人名、单位名里的常用读音（排序按另一读音时纠正）。
const POLYPHONE_INITIALS: Record<string, string> = {
  重: "c", 曾: "z", 单: "s", 解: "x", 仇: "q", 朴: "p", 查: "z", 区: "o", 厦: "x", 尉: "y", 盖: "g",
};

let collator: Intl.Collator | null | undefined;
const getCollator = () => {
  if (collator === undefined) {
    try {
      collator = new Intl.Collator("zh-Hans-CN-u-co-pinyin");
    } catch {
      collator = null;
    }
  }
  return collator;
};

const cache = new Map<string, string>();

const charInitial = (ch: string) => {
  if (/[a-z0-9]/i.test(ch)) return ch.toLowerCase();
  if (!/[一-鿿]/.test(ch)) return "";
  if (POLYPHONE_INITIALS[ch]) return POLYPHONE_INITIALS[ch];
  const zh = getCollator();
  if (!zh) return "";
  let initial = "";
  for (let index = 0; index < INITIAL_BOUNDARIES.length; index += 1) {
    if (zh.compare(ch, INITIAL_BOUNDARIES[index]) >= 0) initial = INITIAL_LETTERS[index];
    else break;
  }
  return initial;
};

/** 文字的拼音首字母串（汉字取首字母，字母数字原样小写，其余忽略）。 */
export function pinyinInitials(text: string): string {
  const key = String(text ?? "");
  const cached = cache.get(key);
  if (cached !== undefined) return cached;
  const value = Array.from(key).map(charInitial).join("");
  if (cache.size > 5000) cache.clear();
  cache.set(key, value);
  return value;
}

/** 选人框匹配：姓名、账号包含关键词，或关键词（纯字母）是姓名拼音首字母的一段。 */
export function personKeywordMatches(keyword: string, ...values: unknown[]): boolean {
  const needle = String(keyword ?? "").trim().toLocaleLowerCase();
  if (!needle) return true;
  const texts = values.map((value) => String(value ?? ""));
  if (texts.some((text) => text.toLocaleLowerCase().includes(needle))) return true;
  if (!/^[a-z]+$/.test(needle)) return false;
  return texts.some((text) => /[一-鿿]/.test(text) && pinyinInitials(text).includes(needle));
}
// pinyin-helpers:end

/**
 * 人员候选仅在输入关键词后显示，已选人员的名称仍由原目录解析。
 * 姓名、账号模糊匹配，也可输入姓名拼音首字母（如 cyd，501629）。
 * listAll：后台固定配置的少量人员（如合同/用印审批人）直接列出，仍可输入关键词过滤（10.26 第6行）。
 */
export function KeywordPersonSelect({ listAll = false, pinnedValues = [], ...props }: SelectProps<any, DefaultOptionType> & { listAll?: boolean; pinnedValues?: string[] }) {
  const [keyword, setKeyword] = useState("");
  const { options: allOptions = [], onSearch, onOpenChange, onSelect, labelRender, notFoundContent, ...rest } = props;
  // 501659：常用的固定选项（如调档费的“外部合作律师”）不用输入就列出，搜索时也排在最前面。
  const pinned = pinnedValues.length ? allOptions.filter(option => pinnedValues.includes(option.value as string)) : [];
  const options = pinned.length ? [...pinned, ...allOptions.filter(option => !pinnedValues.includes(option.value as string))] : allOptions;
  const searching = listAll || Boolean(keyword.trim());
  return <Select
    {...rest}
    showSearch
    optionFilterProp="label"
    filterOption={props.filterOption ?? ((input, option) => personKeywordMatches(input, option?.label, option?.value))}
    searchValue={keyword}
    options={searching ? options : pinned}
    className={["keyword-person-select", props.className].filter(Boolean).join(" ")}
    classNames={info => {
      const names = typeof props.classNames === "function" ? props.classNames(info) : props.classNames;
      return { ...names, popup: { ...names?.popup, root: ["keyword-person-select-popup", names?.popup?.root].filter(Boolean).join(" ") } };
    }}
    labelRender={labelRender || (selected => options.find(option => option.value === selected.value)?.label ?? selected.label ?? selected.value)}
    notFoundContent={searching ? notFoundContent ?? "未找到匹配人员" : "请输入姓名、拼音首字母、账号或部门关键词"}
    onSearch={value => { setKeyword(value); onSearch?.(value); }}
    onClear={() => { setKeyword(""); props.onClear?.(); }}
    onOpenChange={open => { if (!open) setKeyword(""); onOpenChange?.(open); }}
    onSelect={(value, option) => { if (props.autoClearSearchValue !== false) setKeyword(""); onSelect?.(value, option); }}
  />;
}
