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
const refreshIntervalMs = 5 * 60_000;

export function useDashboardData() {
  const [data, setData] = useState<Partial<DashboardData>>({});
  const [loading, setLoading] = useState<Record<DashboardSection, boolean>>({ metrics: true, todos: true, cases: true });
  const [errors, setErrors] = useState<Partial<Record<DashboardSection, string>>>({});
  const [caseMetricsError, setCaseMetricsError] = useState<string>();
  const loader = useRef<(section: DashboardSection) => void>(() => {});
  useEffect(() => {
    let active = true;
    const pending = new Map<DashboardSection, AbortController>();
    const loaded = new Set<DashboardSection>();
    const lastAttempt = new Map<DashboardSection, number>();
    let metricsGeneration = 0;
    let fullMetricsGeneration = 0;
    let caseMetricsController: AbortController | undefined;
    const load = (section: DashboardSection, force = true) => {
      if (!active || pending.has(section)) return;
      if (!force && (document.hidden || Date.now() - (lastAttempt.get(section) ?? 0) < refreshIntervalMs)) return;
      lastAttempt.set(section, Date.now());
      const controller = new AbortController();
      pending.set(section, controller);
      const generation = section === "metrics" ? ++metricsGeneration : 0;
      setLoading((previous) => ({ ...previous, [section]: section === "metrics" || !loaded.has(section) }));
      setErrors((previous) => ({ ...previous, [section]: undefined }));
      if (section === "metrics") {
        caseMetricsController?.abort();
        const caseController = new AbortController();
        caseMetricsController = caseController;
        setCaseMetricsError(undefined);
        // 案件统计独立返回；同一轮的完整统计始终优先，旧轮请求不得写回。
        api.get<Pick<DashboardData, "metrics">>("/dashboard", { params: { section: "metrics_cases" }, signal: caseController.signal })
          .then(({ data: result }) => {
            if (!active || caseController.signal.aborted || generation !== metricsGeneration || fullMetricsGeneration === generation) return;
            setData((previous) => {
              if (generation !== metricsGeneration || fullMetricsGeneration === generation) return previous;
              const metrics = new Map(previous.metrics?.map((metric) => [metric.key, metric]));
              result.metrics.forEach((metric) => metrics.set(metric.key, metric));
              return { ...previous, metrics: Array.from(metrics.values()) };
            });
          })
          .catch((error) => {
            if (!active || caseController.signal.aborted || generation !== metricsGeneration || fullMetricsGeneration === generation) return;
            const detail = error.response?.data?.detail;
            setCaseMetricsError(typeof detail === "string" ? `案件统计加载失败：${detail}` : "案件统计加载失败，请重试");
          });
      }
      api.get<Partial<DashboardData>>("/dashboard", { params: { section }, signal: controller.signal })
        .then(({ data: result }) => {
          if (active && (section !== "metrics" || generation === metricsGeneration)) {
            if (section === "metrics") {
              fullMetricsGeneration = generation;
              caseMetricsController?.abort();
              setCaseMetricsError(undefined);
            }
            loaded.add(section);
            setData((previous) => ({ ...previous, ...result }));
          }
        })
        .catch((error) => {
          if (!active || controller.signal.aborted || (section === "metrics" && generation !== metricsGeneration)) return;
          const detail = error.response?.data?.detail;
          setErrors((previous) => ({ ...previous, [section]: typeof detail === "string" ? detail : "加载失败，请重试" }));
        })
        .finally(() => {
          pending.delete(section);
          if (active && (section !== "metrics" || generation === metricsGeneration)) setLoading((previous) => ({ ...previous, [section]: false }));
        });
    };
    loader.current = load;
    sections.forEach((section) => load(section));
    const refreshStale = () => sections.forEach((section) => load(section, false));
    const timer = window.setInterval(refreshStale, refreshIntervalMs);
    document.addEventListener("visibilitychange", refreshStale);
    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refreshStale);
      pending.forEach((controller) => controller.abort());
      caseMetricsController?.abort();
    };
  }, []);
  const retry = useCallback((section: DashboardSection) => loader.current(section), []);
  return { data, loading, errors, caseMetricsError, retry };
}
