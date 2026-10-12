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
import type { DashboardData } from "./dashboardData";

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
  const pending = metrics.reduce((total, metric) => total + (Number(metric.value) || 0), 0);
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
          {metrics.map((metric, index) => (
            <button type="button" className={`wb-metric tone-${index}${metric.key === "urgent-cases" && Number.parseInt(metric.value, 10) > 0 ? " is-urgent" : ""}`} key={metric.key} onClick={() => onOpen(metric)}>
              <span className="wb-metric-icon">{metricIcons[metric.key]}</span>
              <span className="wb-metric-text">
                <strong>{metric.value}</strong>
                <span>{metric.label}</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
