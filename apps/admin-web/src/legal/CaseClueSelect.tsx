import { useEffect, useState } from "react";
import { message, Select } from "antd";
import { api } from "../api";
import type { CaseRow } from "./types";

export function CaseClueSelect({ caseId, value, onChange }: { caseId?: number; value?: number[]; onChange?: (ids: number[]) => void }) {
  const [items, setItems] = useState<CaseRow[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    setItems([]);
    if (!caseId) return;
    setLoading(true);
    api.get(`/cases/${caseId}/clue-candidates`).then(({ data }) => {
      if (active) setItems(data.items);
    }).catch(error => {
      if (active) message.error(error?.response?.data?.detail || "可关联线索加载失败");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [caseId]);
  return <Select mode="multiple" showSearch optionFilterProp="label" value={value} onChange={onChange}
    loading={loading} placeholder="选择已取证且未生成案件的线索"
    options={items.map(item => ({ value: item.id, label: `${item.serial_no}｜${item.title}` }))} />;
}
