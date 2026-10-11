import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { message } from "antd";
import { api } from "../../api";
import { incomingPaymentQueryParams } from "../services/incomingQuery";
import type { IncomingPayment } from "../types";

export type IncomingPaymentPage = {
  items: IncomingPayment[]; total: number; page: number; page_size: number;
  summary: Record<string, number | null>; totals: Record<string, number | null>;
};

export function useIncomingPaymentQuery(
  view: string, setRows: Dispatch<SetStateAction<IncomingPayment[]>>,
  setSelectedRows: Dispatch<SetStateAction<(string | number)[]>>,
) {
  const [meta, setMeta] = useState({ total: 0, page: 1, pageSize: 20, totals: {} as Record<string, number | null> });
  const [loading, setLoading] = useState(false);
  const current = useRef({ page: 1, pageSize: 20 });
  const sequence = useRef(0);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => { sequence.current += 1; pending.current?.abort(); }, [view]);

  const load = useCallback(async (query: Record<string, unknown>, page = current.current.page, pageSize = current.current.pageSize) => {
    const request = ++sequence.current;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setLoading(true);
    setSelectedRows([]);
    try {
      let response = await api.get<IncomingPaymentPage>("/finance/incoming-payments", {
        params: incomingPaymentQueryParams(view, query, page, pageSize), signal: controller.signal,
      });
      if (request !== sequence.current) return null;
      const lastPage = Math.max(1, Math.ceil(response.data.total / pageSize));
      if (page > lastPage) {
        message.info("当前页已无记录，已返回最后一页");
        response = await api.get<IncomingPaymentPage>("/finance/incoming-payments", {
          params: incomingPaymentQueryParams(view, query, lastPage, pageSize), signal: controller.signal,
        });
        if (request !== sequence.current) return null;
      }
      const { data } = response;
      current.current = { page: data.page, pageSize: data.page_size };
      setRows(data.items);
      setMeta({ total: data.total, page: data.page, pageSize: data.page_size, totals: data.totals });
      return response;
    } catch (error) {
      if (controller.signal.aborted || request !== sequence.current) return null;
      throw error;
    } finally {
      if (request === sequence.current) setLoading(false);
    }
  }, [view, setRows, setSelectedRows]);
  return { meta, loading, load };
}
