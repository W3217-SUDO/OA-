import { useEffect, useRef, useState } from "react";
import { Select } from "antd";
import { api } from "../api";
import type { CaseRow } from "./types";

type Props = {
  caseId?: number; value?: number[]; onChange?: (ids: number[]) => void;
  /** 选择变化时给出已知的线索行（未在候选里的线索不在内），用于带出线索调查员（501293） */
  onPickRows?: (rows: CaseRow[], allKnown: boolean) => void;
};

export function CaseClueSelect(props: Props) {
  return <CaseClueOptions key={props.caseId} {...props} />;
}

function CaseClueOptions({ caseId, value = [], onChange, onPickRows }: Props) {
  const [items, setItems] = useState<CaseRow[]>([]);
  const labels = useRef(new Map<number, CaseRow>());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [keyword, setKeyword] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!caseId) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setItems([]);
    const timer = setTimeout(() => {
      api.get(`/cases/${caseId}/clue-candidates`, {
        params: { keyword }, signal: controller.signal,
      }).then(({ data }) => {
        if (controller.signal.aborted) return;
        const candidates: CaseRow[] = data.items;
        candidates.forEach(item => labels.current.set(item.id, item));
        setItems(candidates);
      }).catch(reason => {
        if (!controller.signal.aborted) {
          setError(reason?.response?.data?.detail || "可关联线索加载失败，请重新打开下拉框重试");
        }
      }).finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    }, keyword ? 250 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [caseId, keyword, refresh]);

  // 搜索结果更新时保留已选线索的名称，但不把旧候选继续作为可选项。
  const selected = new Set(value);
  const options = new Map(items.map(item => [item.id, item]));
  value.forEach(id => {
    const item = labels.current.get(id);
    if (item) options.set(id, item);
  });
  const hasCandidates = items.some(item => !selected.has(item.id));
  const hint = error || (loading ? "正在查询线索…" : keyword
    ? "没有匹配的可关联线索，仅支持同客户、已取证且未生成案件的线索"
    : "暂无符合条件的线索，仅支持同客户、已取证且未生成案件的线索");
  const change = (ids: number[]) => {
    onChange?.(ids);
    const rows = ids.map(id => labels.current.get(id)).filter((item): item is CaseRow => Boolean(item));
    onPickRows?.(rows, rows.length === ids.length);
  };
  return <Select mode="multiple" showSearch filterOption={false} value={value} onChange={change}
    loading={loading} searchValue={keyword} onSearch={setKeyword}
    onOpenChange={open => { if (open) { setKeyword(""); setRefresh(count => count + 1); } }}
    placeholder="选择已取证且未生成案件的线索"
    notFoundContent={hint}
    popupRender={menu => <>{hasCandidates ? menu : <div style={{ padding: "8px 12px", color: error ? "#cf1322" : "#666" }}>{hint}</div>}</>}
    options={[...options.values()].map(item => ({
      value: item.id, label: `${item.serial_no}｜${item.title}`,
      style: selected.has(item.id) ? { display: "none" } : undefined,
    }))} />;
}
