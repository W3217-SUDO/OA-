import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api";
import type { CaseRow } from "../types";

type ReceiptQuery = Record<string, string>;

export function useReceiptCases(route: string) {
  const active = route === "case-files-receipt";
  const [rows, setRows] = useState<CaseRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(active);
  const [error, setError] = useState("");
  const sequence = useRef(0);
  const current = useRef({ query: {} as ReceiptQuery, page: 1, pageSize: 20 });

  const search = useCallback(async (
    query: ReceiptQuery = current.current.query,
    nextPage = current.current.page,
    nextSize = current.current.pageSize,
  ) => {
    if (!active) return;
    const request = ++sequence.current;
    current.current = { query, page: nextPage, pageSize: nextSize };
    setPage(nextPage);
    setPageSize(nextSize);
    setLoading(true);
    setError("");
    try {
      const { status, ...fields } = query;
      const { data } = await api.get("/records", {
        params: {
          module: "case",
          page: nextPage,
          page_size: nextSize,
          ...Object.fromEntries(Object.entries(fields).filter(([, value]) => String(value || "").trim())),
          ...(status?.trim() ? { case_stage: status.trim() } : {}),
        },
      });
      if (request !== sequence.current) return;
      setRows(data.items);
      setTotal(data.total);
    } catch (failure: any) {
      if (request !== sequence.current) return;
      setRows([]);
      setTotal(0);
      const detail = failure?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "案件票据文件列表加载失败，请重试");
    } finally {
      if (request === sequence.current) setLoading(false);
    }
  }, [active]);

  useEffect(() => {
    current.current = { query: {}, page: 1, pageSize: 20 };
    setRows([]);
    setTotal(0);
    void search({}, 1, 20);
    return () => { sequence.current += 1; };
  }, [route, search]);

  return { rows, total, page, pageSize, loading, error, search, reload: () => search() };
}
