import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api";
import type { CaseRow, Hearing } from "../types";

type SpecialCaseRow = CaseRow | (Omit<Hearing, "id"> & { id: string; case: CaseRow });

function queryParams(query: Record<string, any>, kind: string, scope: string, page: number, pageSize: number) {
  const { payment_range, hearing_range, source_range, handling_lawyer, ...filters } = query;
  return {
    ...Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== "")),
    kind, scope, page, page_size: pageSize,
    ...(kind === "schedule" ? {
      handling_lawyer,
      hearing_from: hearing_range?.[0]?.format("YYYY-MM-DD"),
      hearing_to: hearing_range?.[1]?.format("YYYY-MM-DD"),
      source_from: source_range?.[0]?.format("YYYY-MM-DD"),
      source_to: source_range?.[1]?.format("YYYY-MM-DD"),
    } : {}),
    ...(payment_range?.length === 2 ? {
      paid_from: payment_range[0].format("YYYY-MM-DD"),
      paid_to: payment_range[1].format("YYYY-MM-DD"),
    } : {}),
  };
}

export function useSpecialCaseRecords(route: string) {
  const kind = route === "case-company-schedule" ? "schedule" : route.endsWith("-unclaimed") ? "unclaimed" : route.endsWith("-no-refund") ? "refund" : "";
  const scope = route.startsWith("case-mine") ? "mine" : route.startsWith("case-dept") ? "department" : "company";
  const [rows, setRows] = useState<SpecialCaseRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(Boolean(kind));
  const [error, setError] = useState("");
  const sequence = useRef(0);
  const current = useRef({ query: {} as Record<string, any>, page: 1, pageSize: 20 });

  const search = useCallback(async (
    query: Record<string, any> = current.current.query,
    nextPage = current.current.page,
    nextSize = current.current.pageSize,
  ) => {
    if (!kind) return false;
    const request = ++sequence.current;
    current.current = { query, page: nextPage, pageSize: nextSize };
    setPage(nextPage);
    setPageSize(nextSize);
    setRows([]);
    setTotal(0);
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/cases/special-records", {
        params: queryParams(query, kind, scope, nextPage, nextSize),
      });
      if (request !== sequence.current) return false;
      setRows(data.items);
      setTotal(data.total);
      return true;
    } catch (failure: any) {
      if (request !== sequence.current) return false;
      const detail = failure?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "案件查询失败，请重试");
      return false;
    } finally {
      if (request === sequence.current) setLoading(false);
    }
  }, [kind, scope]);

  useEffect(() => {
    current.current = { query: {}, page: 1, pageSize: 20 };
    setRows([]);
    setTotal(0);
    setPage(1);
    setPageSize(20);
    setError("");
    return () => { sequence.current += 1; };
  }, [route]);

  const exportFile = () => api.get<Blob>("/cases/special-records", {
    params: { ...queryParams(current.current.query, kind, scope, 1, 200), export_format: "xls" },
    responseType: "blob",
  });

  return { active: Boolean(kind), rows, total, page, pageSize, loading, error, search, exportFile, reload: () => search() };
}
