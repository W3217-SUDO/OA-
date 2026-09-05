import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api";
import type { CaseRow } from "../types";

type Query = Record<string, any>;
export function useArchiveCases(route: string) {
  const active = route.startsWith("case-archive-");
  const view = route.includes("done") ? "done" : route.includes("refused") ? "refused" : "pending";
  const [rows, setRows] = useState<CaseRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(view === "pending" ? 15 : 10);
  const [loading, setLoading] = useState(active);
  const [error, setError] = useState("");
  const sequence = useRef(0);
  const current = useRef({ query: {} as Query, page: 1, pageSize: view === "pending" ? 15 : 10 });
  const exportFile = async (format: "excel" | "csv", selectedIds?: number[]) => {
    const { review_range, submit_range, ...fields } = current.current.query;
    const date = (value: any) => value?.format?.("YYYY-MM-DD") || undefined;
    return api.post("/cases/archive/export", { ...fields, view, format, selected_ids: selectedIds,
      review_from: date(review_range?.[0]), review_to: date(review_range?.[1]),
      submit_from: date(submit_range?.[0]), submit_to: date(submit_range?.[1]),
    }, { responseType: "blob" });
  };
  const search = useCallback(async (query: Query = current.current.query, nextPage = current.current.page, nextSize = current.current.pageSize) => {
    if (!active) return;
    const request = ++sequence.current;
    current.current = { query, page: nextPage, pageSize: nextSize };
    setPage(nextPage); setPageSize(nextSize); setLoading(true); setError("");
    const { review_range, submit_range, ...fields } = query;
    const date = (value: any) => value?.format?.("YYYY-MM-DD") || undefined;
    const payload = { ...fields, view, page: nextPage, page_size: nextSize,
      review_from: date(review_range?.[0]), review_to: date(review_range?.[1]),
      submit_from: date(submit_range?.[0]), submit_to: date(submit_range?.[1]) };
    try {
      let { data } = await api.post("/cases/archive/search", payload);
      if (request !== sequence.current) return;
      const lastPage = Math.max(1, Math.ceil(data.total / nextSize));
      if (nextPage > lastPage) {
        ({ data } = await api.post("/cases/archive/search", { ...payload, page: lastPage }));
        if (request !== sequence.current) return;
        current.current.page = lastPage; setPage(lastPage);
      }
      setRows(data.items); setTotal(data.total);
    } catch (failure: any) {
      if (request !== sequence.current) return;
      setRows([]); setTotal(0);
      const detail = failure?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "归档案件加载失败，请重试");
    } finally {
      if (request === sequence.current) setLoading(false);
    }
  }, [active, view]);
  useEffect(() => {
    setRows([]); setTotal(0);
    void search({}, 1, view === "pending" ? 15 : 10);
    return () => { sequence.current += 1; };
  }, [route, search, view]);
  return { rows, total, page, pageSize, loading, error, search, exportFile, reload: () => search() };
}
