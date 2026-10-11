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
    let caseMetricsController: AbortController | undefined;
    const load = (section: DashboardSection, force = true) => {
      if (!active || pending.has(section)) return;
      if (!force && (document.hidden || Date.now() - (lastAttempt.get(section) ?? 0) < refreshIntervalMs)) return;
      lastAttempt.set(section, Date.now());
      const controller = new AbortController();
      pending.set(section, controller);
      const generation = section === "metrics" ? ++metricsGeneration : 0;
      let remaining = section === "metrics" ? 2 : 1;
      const finish = () => {
        if (--remaining > 0 || pending.get(section) !== controller) return;
        pending.delete(section);
        if (active && (section !== "metrics" || generation === metricsGeneration)) {
          setLoading((previous) => ({ ...previous, [section]: false }));
        }
      };
      setLoading((previous) => ({ ...previous, [section]: section === "metrics" || !loaded.has(section) }));
      setErrors((previous) => ({ ...previous, [section]: undefined }));
      if (section === "metrics") {
        caseMetricsController?.abort();
        const caseController = new AbortController();
        caseMetricsController = caseController;
        setCaseMetricsError(undefined);
        // 两组真实指标按键独立合并；任一组先返回都不能覆盖或取消另一组。
        const loadMetrics = (
          apiSection: "metrics_cases" | "metrics_finance",
          requestController: AbortController,
          onError: (detail: string | undefined) => void,
        ) => {
          api.get<Pick<DashboardData, "metrics">>("/dashboard", { params: { section: apiSection }, signal: requestController.signal })
            .then(({ data: result }) => {
              if (!active || requestController.signal.aborted || generation !== metricsGeneration) return;
              loaded.add(section);
              setData((previous) => {
                if (!active || requestController.signal.aborted || generation !== metricsGeneration) return previous;
                const metrics = new Map(previous.metrics?.map((metric) => [metric.key, metric]));
                result.metrics.forEach((metric) => metrics.set(metric.key, metric));
                return { ...previous, metrics: Array.from(metrics.values()) };
              });
            })
            .catch((error) => {
              if (!active || requestController.signal.aborted || generation !== metricsGeneration) return;
              const detail = error.response?.data?.detail;
              onError(typeof detail === "string" ? detail : undefined);
            })
            .finally(finish);
        };
        loadMetrics("metrics_cases", caseController, (detail) => {
          setCaseMetricsError(detail !== undefined ? `案件统计加载失败：${detail}` : "案件统计加载失败，请重试");
        });
        loadMetrics("metrics_finance", controller, (detail) => {
          setErrors((previous) => ({ ...previous, metrics: detail ?? "加载失败，请重试" }));
        });
        return;
      }
      api.get<Partial<DashboardData>>("/dashboard", { params: { section }, signal: controller.signal })
        .then(({ data: result }) => {
          if (active && !controller.signal.aborted) {
            loaded.add(section);
            setData((previous) => ({ ...previous, ...result }));
          }
        })
        .catch((error) => {
          if (!active || controller.signal.aborted) return;
          const detail = error.response?.data?.detail;
          setErrors((previous) => ({ ...previous, [section]: typeof detail === "string" ? detail : "加载失败，请重试" }));
        })
        .finally(finish);
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
