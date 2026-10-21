import { useState } from "react";
import { Select } from "antd";
import type { SelectProps } from "antd";
import type { DefaultOptionType } from "antd/es/select";
import "./keyword-person-select.css";

/** 人员候选仅在输入关键词后显示，已选人员的名称仍由原目录解析。 */
export function KeywordPersonSelect(props: SelectProps<any, DefaultOptionType>) {
  const [keyword, setKeyword] = useState("");
  const { options = [], onSearch, onOpenChange, onSelect, labelRender, notFoundContent, ...rest } = props;
  const searching = Boolean(keyword.trim());
  return <Select
    {...rest}
    showSearch
    optionFilterProp="label"
    filterOption={props.filterOption ?? ((input, option) => [option?.label, option?.value].some(value => String(value ?? "").toLocaleLowerCase().includes(input.trim().toLocaleLowerCase())))}
    searchValue={keyword}
    options={searching ? options : []}
    className={["keyword-person-select", props.className].filter(Boolean).join(" ")}
    classNames={info => {
      const names = typeof props.classNames === "function" ? props.classNames(info) : props.classNames;
      return { ...names, popup: { ...names?.popup, root: ["keyword-person-select-popup", names?.popup?.root].filter(Boolean).join(" ") } };
    }}
    labelRender={labelRender || (selected => options.find(option => option.value === selected.value)?.label ?? selected.label ?? selected.value)}
    notFoundContent={searching ? notFoundContent ?? "未找到匹配人员" : "请输入姓名、账号或部门关键词"}
    onSearch={value => { setKeyword(value); onSearch?.(value); }}
    onClear={() => { setKeyword(""); props.onClear?.(); }}
    onOpenChange={open => { if (!open) setKeyword(""); onOpenChange?.(open); }}
    onSelect={(value, option) => { if (props.autoClearSearchValue !== false) setKeyword(""); onSelect?.(value, option); }}
  />;
}
