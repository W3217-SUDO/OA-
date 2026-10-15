import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { financeErrorDetail } from "../financeErrors";
import type { Fee, FinanceInternalQueueMeta } from "../types";

const internalQueries: Record<string, { path: string; scope?: string; kind?: string }> = {
  // Internal applications are a separate queue from external payment
  // management. Keep this route on the paginated internal-fee API so the
  // menu entry cannot accidentally fall through to finance-payment-mine.
  "finance-internal-mine": { path: "/finance/internal-fees", scope: "applications" },
  "finance-internal-settle": { path: "/finance/settlements/pending" },
  "finance-internal-archive": { path: "/finance/internal-fees", scope: "archive" },
  "finance-internal-refused": { path: "/finance/internal-fees", scope: "refused" },
  "finance-internal-payment": { path: "/finance/internal-fees", scope: "payment" },
  "finance-internal-audit": { path: "/finance/internal-review-requests", kind: "commission" },
  "finance-internal-fee-audit": { path: "/finance/internal-review-requests", kind: "other" },
  "finance-internal-refund-audit": { path: "/finance/internal-review-requests", kind: "refund" },
};

export const isInternalFinanceQuery = (route: string) => Boolean(internalQueries[route]);

export function internalFinanceQueryRequest(route: string, query: Record<string, unknown>, page: number, pageSize: number) {
  const target = internalQueries[route];
  if (!target) throw new Error("内部费用查询入口无效");
  const { path, ...scope } = target;
  const params: Record<string, unknown> = { ...scope, page, page_size: pageSize };
  const dateRange = (key: string, value: unknown) => {
    if (!Array.isArray(value)) return;
    params[`${key}_from`] = value[0]?.format?.("YYYY-MM-DD");
    params[`${key}_to`] = value[1]?.format?.("YYYY-MM-DD");
  };
  const fields = route === "finance-internal-settle"
    ? ["customer", "case_no", "court_case_no", "certificate_no", "hearing_lawyer", "assistant", "case_stages", "investigator", "source_person"]
    : route === "finance-internal-mine"
      ? ["application", "status", "applicant", "audit", "case_no", "application_no", "customer", "case_stages", "fee_types"]
    : route === "finance-internal-payment"
      ? ["application", "status", "payee", "audit", "case_no", "applicant", "customer", "case_stages", "fee_types"]
      : route === "finance-internal-refused"
        ? ["application", "status", "applicant", "audit", "case_no", "application_no", "customer", "case_stages", "fee_types"]
        : ["application", "status", "applicant", "paid", "customer", "case_no", "application_no", "case_stages", "fee_types"];
  fields.forEach((field, index) => {
    const value = query[`routeField${index}`];
    if (value == null || value === "" || value === "请选择" || value === "全部") return;
    if (["application", "audit", "paid"].includes(field)) dateRange(field, value);
    else if (field === "status" && ["finance-internal-refused", "finance-internal-refund-audit"].includes(route)) params.request_status = value;
    else if (field !== "status") params[field] = Array.isArray(value) ? value.join(",") : value;
  });
  return { path, params };
}

export function useInternalFinanceQuery(route: string, clearSelection: (keys: (string | number)[]) => void) {
  const [rows, setRows] = useState<Fee[]>([]);
  const [meta, setMeta] = useState<FinanceInternalQueueMeta>({ page: 1, pageSize: 15, total: 0, amountVisible: false, totalAmount: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const current = useRef({ page: 1, pageSize: 15 });
  const sequence = useRef(0);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => {
    current.current = { page: 1, pageSize: 15 };
    setRows([]);
    setError(null);
    setMeta({ page: 1, pageSize: 15, total: 0, amountVisible: false, totalAmount: null });
    return () => { sequence.current += 1; pending.current?.abort(); };
  }, [route]);
  const load = useCallback(async (query: Record<string, unknown>, page = current.current.page, pageSize = current.current.pageSize) => {
    const request = ++sequence.current;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    clearSelection([]);
    setLoading(true);
    setError(null);
    try {
      const { path, params } = internalFinanceQueryRequest(route, query, page, pageSize);
      const response = await api.get(path, { params, signal: controller.signal });
      if (controller.signal.aborted || request !== sequence.current) return null;
      const { data } = response;
      if (!Array.isArray(data.items) || !Number.isInteger(data.total) || data.total < 0
          || !Number.isInteger(data.page) || data.page < 1 || !Number.isInteger(data.page_size) || data.page_size < 1) {
        throw new Error("内部费用分页响应无效");
      }
      const validAmount = (value: unknown) => data.amount_visible ? Number.isFinite(value) : value === null;
      if (typeof data.amount_visible !== "boolean" || !validAmount(data.total_amount)
          || (route === "finance-internal-payment" && !validAmount(data.total_actual_commission))
          || (route === "finance-internal-settle" && !validAmount(data.total_cashed_amount))) {
        throw new Error("内部费用汇总响应无效");
      }
      current.current = { page: data.page, pageSize: data.page_size };
      setRows(data.items);
      setMeta({ ...current.current, total: data.total, amountVisible: data.amount_visible,
        totalAmount: data.total_amount, totalActualCommission: data.total_actual_commission, totalCashedAmount: data.total_cashed_amount });
      return response;
    } catch (cause) {
      if (controller.signal.aborted || request !== sequence.current) return null;
      setRows([]);
      setError(financeErrorDetail(cause) || "内部费用查询失败");
      throw cause;
    } finally {
      if (request === sequence.current) setLoading(false);
    }
  }, [route, clearSelection]);
  return { rows, meta, loading, error, load };
}
