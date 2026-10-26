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
  rejections: DashboardRejection[];
  rejection_total: number;
  // 首页分端待办（系统参数“首页分端待办”）：当前账号能看的端、待办目录、目录里由分端模块单独统计的数字。
  portals: DashboardPortal[];
  portal_items: DashboardPortalItem[];
  portal_counts: Record<string, number>;
};

export type DashboardPortal = { key: string; name: string; items: string[] };
export type DashboardPortalItem = { key: string; label: string; route: string; source: string; description: string };

export type DashboardRejection = {
  id: number;
  type: string;
  serial_no: string;
  title: string;
  reason: string;
  rejected_by: string;
  rejected_at: string;
  route: string;
};

// 10.23 第4行：八个提醒指标的固定顺序，与后端 dashboard_metrics.METRIC_DEFINITIONS（原八卡）一致。
// 案件、财务两组指标分两个接口并行加载，必须按此顺序排列，不能按返回先后拼接。
export const DASHBOARD_METRIC_ORDER: { key: string; label: string }[] = [
  { key: "official-fee-unpaid", label: "待缴官费" },
  { key: "refund-pending", label: "待退费" },
  { key: "evidence-supplement", label: "补充证据" },
  { key: "opinion-supplement", label: "补充意见" },
  { key: "appeal-pending", label: "待上诉" },
  { key: "execution-pending", label: "待执行" },
  { key: "urgent-cases", label: "紧急案件" },
  { key: "official-fee-unreceived", label: "未到官费金额" },
];

const metricRank = (key: string) => {
  const index = DASHBOARD_METRIC_ORDER.findIndex((item) => item.key === key);
  return index < 0 ? DASHBOARD_METRIC_ORDER.length : index;
};

export const orderDashboardMetrics = <T extends { key: string }>(metrics: T[]): T[] =>
  metrics.map((metric, index) => ({ metric, index }))
    .sort((left, right) => metricRank(left.metric.key) - metricRank(right.metric.key) || left.index - right.index)
    .map(({ metric }) => metric);

export type DashboardSection = "metrics" | "todos" | "cases" | "rejections" | "portals";
const sections: DashboardSection[] = ["metrics", "todos", "cases", "rejections", "portals"];
const refreshIntervalMs = 5 * 60_000;

export function useDashboardData(requestedSections: readonly DashboardSection[] = sections) {
  const [data, setData] = useState<Partial<DashboardData>>({});
  const [loading, setLoading] = useState<Record<DashboardSection, boolean>>({ metrics: true, todos: true, cases: true, rejections: true, portals: true });
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
                return { ...previous, metrics: orderDashboardMetrics(Array.from(metrics.values())) };
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
    requestedSections.forEach((section) => load(section));
    const refreshStale = () => requestedSections.forEach((section) => load(section, false));
    const timer = window.setInterval(refreshStale, refreshIntervalMs);
    document.addEventListener("visibilitychange", refreshStale);
    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refreshStale);
      pending.forEach((controller) => controller.abort());
      caseMetricsController?.abort();
    };
  }, [requestedSections]);
  const retry = useCallback((section: DashboardSection) => loader.current(section), []);
  return { data, loading, errors, caseMetricsError, retry };
}
