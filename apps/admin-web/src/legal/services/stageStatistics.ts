import { useEffect, useState } from "react";
import { api } from "../../api";

type StageRow = { id: string; name: string; date: string; values: number[] };

export function useStageStatistics(active: boolean) {
  const [rows, setRows] = useState<StageRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/cases/stage-statistics");
      setRows(response.data.items);
    } catch (failure: any) {
      setRows([]);
      setError(failure?.response?.data?.detail || "案件阶段统计加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { if (active) void load(); }, [active]);
  const sum = (values: number[], start: number, end: number) => values.slice(start, end).reduce((total, value) => total + value, 0);
  return {
    loading, error, load,
    rows: rows.map(row => ({ id: row.id, name: row.name, date: row.date,
      filing: sum(row.values, 0, 8), refund: sum(row.values, 8, 13),
      execution: sum(row.values, 13, 24), clue: sum(row.values, 24, 28) })),
  };
}
