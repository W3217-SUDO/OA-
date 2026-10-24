import { useEffect, useState, type ReactNode } from "react";
import { Button } from "antd";
import {
  AlertOutlined,
  ClockCircleOutlined,
  DownOutlined,
  EditOutlined,
  FileSearchOutlined,
  FlagOutlined,
  PayCircleOutlined,
  ProfileOutlined,
  RollbackOutlined,
} from "@ant-design/icons";
import { DASHBOARD_METRIC_ORDER, orderDashboardMetrics, type DashboardData } from "./dashboardData";

type Metric = DashboardData["metrics"][number];

const metricIcons: Record<string, ReactNode> = {
  "official-fee-unpaid": <ClockCircleOutlined />,
  "refund-pending": <RollbackOutlined />,
  "evidence-supplement": <FileSearchOutlined />,
  "opinion-supplement": <EditOutlined />,
  "appeal-pending": <FlagOutlined />,
  "execution-pending": <ProfileOutlined />,
  "urgent-cases": <AlertOutlined />,
  "official-fee-unreceived": <PayCircleOutlined />,
};

// “356件”“2921498.23元”拆成数字和单位，数字醒目、单位缩小。
function splitValue(value: string) {
  const match = /^([-+]?[\d,]+(?:\.\d+)?)(.*)$/.exec(value.trim());
  return match ? { number: match[1], unit: match[2], zero: Number(match[1].replace(/,/g, "")) === 0 } : { number: value, unit: "", zero: false };
}

const COLLAPSE_KEY = "sunhold:workbench-metrics-collapsed";

type Props = {
  metrics: Metric[];
  status: ReactNode;
  onOpen: (metric: Metric) => void;
};

// 折叠状态只影响工作台这一块，刷新后保持。用户没手动设置过时，窄屏默认收起，减少首屏占用。
function readCollapsed() {
  try {
    const stored = window.localStorage.getItem(COLLAPSE_KEY);
    if (stored !== null) return stored === "1";
  } catch {
    // 浏览器禁用本地存储时按窄屏默认值处理。
  }
  return window.innerWidth < 721;
}

// 提醒指标：八个色块加一个折叠开关，收起来时只留一行摘要，不承载问候语。
export default function DashboardMetricTiles({ metrics, status, onOpen }: Props) {
  const [collapsed, setCollapsed] = useState(readCollapsed);
  useEffect(() => {
    try {
      window.localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
    } catch {
      // 浏览器禁用本地存储时仍然可以折叠，只是不记忆状态。
    }
  }, [collapsed]);
  // 10.23 第4行：八个位置固定（未返回的一组先占位），颜色按指标固定，不随位置变化。
  const known = new Set(DASHBOARD_METRIC_ORDER.map((item) => item.key));
  const byKey = new Map(metrics.map((metric) => [metric.key, metric]));
  const slots = [
    ...DASHBOARD_METRIC_ORDER.map((item, tone) => ({ key: item.key, label: item.label, metric: byKey.get(item.key), tone })),
    ...orderDashboardMetrics(metrics.filter((metric) => !known.has(metric.key)))
      .map((metric, index) => ({ key: metric.key, label: metric.label, metric, tone: (DASHBOARD_METRIC_ORDER.length + index) % 8 })),
  ];
  // 指标值带单位（如“356件”），只累计按“件”计的数量；金额不计入待办件数。
  const pending = metrics.reduce((total, metric) => {
    const value = splitValue(metric.value);
    return value.unit === "件" ? total + (Number(value.number.replace(/,/g, "")) || 0) : total;
  }, 0);
  return (
    <section className={`wb-metrics${collapsed ? " is-collapsed" : ""}`} aria-label="案件与费用提醒">
      <div className="wb-metric-bar">
        {status}
        <Button
          type="text"
          size="small"
          className="wb-metric-toggle"
          aria-expanded={!collapsed}
          aria-label={collapsed ? "展开提醒指标" : "收起提醒指标"}
          onClick={() => setCollapsed((value) => !value)}
        >
          <DownOutlined />提醒指标
        </Button>
        {collapsed && <span className="wb-metric-summary">共 {metrics.length} 项，待办 {pending} 件</span>}
      </div>
      {!collapsed && (
        <div className="wb-metric-grid">
          {slots.map(({ key, label, metric, tone }) => {
            if (!metric) return (
              <button type="button" className={`wb-metric tone-${tone} is-loading`} key={key} disabled aria-busy="true">
                <span className="wb-metric-icon">{metricIcons[key]}</span>
                <span className="wb-metric-text">
                  <strong>…</strong>
                  <span>{label}</span>
                </span>
              </button>
            );
            const value = splitValue(metric.value);
            // 统一用主题色；为 0 的数字变灰；紧急案件有数时整块变红，红色只用在这里。
            const state = value.zero ? " is-clear" : metric.key === "urgent-cases" ? " has-pending is-urgent" : " has-pending";
            return (
              <button type="button" className={`wb-metric tone-${tone}${state}${metric.key === "official-fee-unreceived" ? " is-wide" : ""}`} key={key} onClick={() => onOpen(metric)} aria-label={`${metric.label} ${metric.value}`}>
                <span className="wb-metric-icon">{metricIcons[metric.key]}</span>
                <span className="wb-metric-text">
                  <strong><b className="wb-metric-number">{value.number}</b>{value.unit && <small>{value.unit}</small>}</strong>
                  <span>{metric.label}</span>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
