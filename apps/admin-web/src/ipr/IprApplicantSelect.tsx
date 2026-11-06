import { Select } from "antd";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";

// 501187：申请人边输边搜已有客户、当事人和非诉申请人库，选中带入；搜不到可以手填，保存时后台登记到申请人库，
// 名称和已有的完全一样时直接用已有的，不重复新建。
type Value = string | string[] | undefined;
const SEPARATORS = /[,，、;；]/;
const toList = (value: Value) => (Array.isArray(value) ? value : String(value || "").split(SEPARATORS))
  .map((item) => item.trim()).filter(Boolean);

export function IprApplicantSelect({ value, onChange, size, asText }: {
  value?: Value; onChange?: (value: any) => void; size?: "small" | "middle"; asText?: boolean;
}) {
  const [options, setOptions] = useState<{ value: string; label: string }[]>([]);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const search = (keyword: string) => {
    window.clearTimeout(timer.current);
    if (!keyword.trim()) { setOptions([]); return; }
    timer.current = window.setTimeout(() => {
      api.get<{ items: { value: string; source: string }[] }>("/ipr/applicant-options", { params: { keyword } })
        .then(({ data }) => setOptions((data.items || []).map((item) => ({ value: item.value, label: `${item.value}（${item.source}）` }))))
        .catch(() => setOptions([]));
    }, 250);
  };
  return (
    <Select
      mode="tags"
      size={size}
      style={{ width: "100%" }}
      value={toList(value)}
      options={options}
      filterOption={false}
      tokenSeparators={[",", "，", "、"]}
      placeholder="输入名称搜索；搜不到可直接填写"
      onSearch={search}
      onChange={(next: string[]) => { setOptions([]); onChange?.(asText ? next.join("，") : next); }}
      notFoundContent={null}
    />
  );
}
