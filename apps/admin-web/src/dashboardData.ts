import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

export type DashboardData = {
  metrics: {
    key: string;
    label: string;
    value: string;
    tone: string;
    route: string;
    query?: { scope?: "mine" | "company"; unpaid_official?: boolean };
    detail_context?: { contract_no: string; return_view: string; amount_filter?: string; owner?: string };
  }[];
  todos: (string | number)[][];
  hearings: Record<string, string>[];
  latest_cases: Record<string, string>[];
  case_trend: { date: string; value: number }[];
  civil_distribution: { label: string; value: number; color: string }[];
};

export type DashboardSection = "metrics" | "todos" | "cases";
const sections: DashboardSection[] = ["metrics", "todos", "cases"];

export function useDashboardData() {
  const [data, setData] = useState<Partial<DashboardData>>({});
  const [loading, setLoading] = useState<Record<DashboardSection, boolean>>({ metrics: true, todos: true, cases: true });
  const [errors, setErrors] = useState<Partial<Record<DashboardSection, string>>>({});
  const loader = useRef<(section: DashboardSection) => void>(() => {});
  useEffect(() => {
    let active = true;
    const pending = new Map<DashboardSection, AbortController>();
    const load = (section: DashboardSection) => {
      if (!active || pending.has(section)) return;
      const controller = new AbortController();
      pending.set(section, controller);
      setLoading((previous) => ({ ...previous, [section]: true }));
      setErrors((previous) => ({ ...previous, [section]: undefined }));
      api.get<Partial<DashboardData>>("/dashboard", { params: { section }, signal: controller.signal })
        .then(({ data: result }) => {
          if (active) setData((previous) => ({ ...previous, ...result }));
        })
        .catch((error) => {
          if (!active || controller.signal.aborted) return;
          const detail = error.response?.data?.detail;
          setErrors((previous) => ({ ...previous, [section]: typeof detail === "string" ? detail : "加载失败，请重试" }));
        })
        .finally(() => {
          pending.delete(section);
          if (active) setLoading((previous) => ({ ...previous, [section]: false }));
        });
    };
    loader.current = load;
    const refresh = () => sections.forEach(load);
    refresh();
    const timer = window.setInterval(refresh, 30_000);
    window.addEventListener("focus", refresh);
    return () => {
      active = false;
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
      pending.forEach((controller) => controller.abort());
    };
  }, []);
  const retry = useCallback((section: DashboardSection) => loader.current(section), []);
  return { data, loading, errors, retry };
}
