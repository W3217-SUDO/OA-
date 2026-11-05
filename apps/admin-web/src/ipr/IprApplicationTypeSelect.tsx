import { Select } from "antd";
import { useEffect, useState } from "react";
import { api } from "../api";

// 501611（fwl 11-05）：申请类型下拉，选项来自系统参数“知识产权申请类型”（照旧系统，可维护）。
// 已有案件里不在选项中的原值（如手填的“发明”）照原样显示，可以改选。
let cache: Promise<string[]> | null = null;
const loadOptions = () => {
  cache ??= api.get<{ items: { name: string }[] }>("/system/parameters/options", { params: { category: "ipr_application_type" } })
    .then(({ data }) => (data.items || []).map((item) => item.name))
    .catch(() => { cache = null; return []; });
  return cache;
};

export function IprApplicationTypeSelect({ value, onChange }: { value?: string; onChange?: (value: string | undefined) => void }) {
  const [names, setNames] = useState<string[]>([]);
  useEffect(() => { let alive = true; void loadOptions().then((items) => { if (alive) setNames(items); }); return () => { alive = false; }; }, []);
  const options = names.map((name) => ({ value: name, label: name }));
  if (value && !names.includes(value)) options.unshift({ value, label: `${value}（原值，不在选项里）` });
  return <Select showSearch allowClear placeholder="请选择申请类型" optionFilterProp="label" value={value || undefined}
    onChange={(next) => onChange?.(next ?? undefined)} options={options} />;
}
