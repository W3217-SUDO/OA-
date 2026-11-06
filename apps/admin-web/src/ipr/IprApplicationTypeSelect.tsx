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

// 501187：按专利或商标列类型；软著、高新认定等不属于两边的两边都列。
const belongsToOtherKind = (name: string, kind?: string) => {
  const trademark = name.includes("商标");
  const patent = /专利|PCT|外观设计/.test(name);
  return kind === "专利" ? trademark : kind === "商标" ? patent : false;
};

export function IprApplicationTypeSelect({ value, onChange, caseKind, size }: { caseKind?: string; size?: "small" | "middle"; value?: string; onChange?: (value: string | undefined) => void }) {
  const [names, setNames] = useState<string[]>([]);
  useEffect(() => { let alive = true; void loadOptions().then((items) => { if (alive) setNames(items); }); return () => { alive = false; }; }, []);
  const options = names.filter((name) => !belongsToOtherKind(name, caseKind)).map((name) => ({ value: name, label: name }));
  if (value && !names.includes(value)) options.unshift({ value, label: `${value}（原值，不在选项里）` });
  return <Select size={size} showSearch allowClear placeholder="请选择申请类型" optionFilterProp="label" value={value || undefined}
    onChange={(next) => onChange?.(next ?? undefined)} options={options} />;
}

// 501612（fwl 11-05）：案件阶段下拉，照旧系统按申请类型给出阶段；已有值不在选项里时照原样显示。
const phaseCache = new Map<string, Promise<string[]>>();
const loadPhases = (applicationType: string) => {
  if (!phaseCache.has(applicationType)) {
    phaseCache.set(applicationType, api.get<{ items: string[] }>("/ipr/phase-options", { params: { application_type: applicationType } })
      .then(({ data }) => data.items || [])
      .catch(() => { phaseCache.delete(applicationType); return []; }));
  }
  return phaseCache.get(applicationType)!;
};

export function IprPhaseSelect({ value, onChange, applicationType }: { value?: string; onChange?: (value: string | undefined) => void; applicationType?: string }) {
  const [names, setNames] = useState<string[]>([]);
  useEffect(() => { let alive = true; void loadPhases(applicationType || "").then((items) => { if (alive) setNames(items); }); return () => { alive = false; }; }, [applicationType]);
  const options = names.map((name) => ({ value: name, label: name }));
  if (value && names.length && !names.includes(value)) options.unshift({ value, label: `${value}（当前阶段，不在该类型的选项里）` });
  return <Select showSearch placeholder="请选择案件阶段" optionFilterProp="label" value={value || undefined}
    onChange={(next) => onChange?.(next ?? undefined)} options={options} />;
}
