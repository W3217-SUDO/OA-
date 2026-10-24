import { AlertOutlined, BellFilled, CheckCircleFilled } from "@ant-design/icons";
import type { DashboardData } from "./dashboardData";
import { dashboardTodoItems, prepareTodoNavigation } from "./dashboardTodos";

type Metric = DashboardData["metrics"][number];

type Props = {
  todos?: DashboardData["todos"];
  metrics?: DashboardData["metrics"];
  loading: boolean;
  canNavigate: (route: string) => boolean;
  onNavigate: (route: string) => void;
  onOpenMetric: (metric: Metric) => void;
};

// 问候语旁的“优先处理”：紧急案件排第一，其余按积压件数从多到少取前几项，点一下直接进对应列表。
export default function DashboardFocus({ todos, metrics, loading, canNavigate, onNavigate, onOpenMetric }: Props) {
  if (loading) return null;
  const urgent = (metrics || []).find((metric) => metric.key === "urgent-cases");
  const urgentCount = urgent ? Number.parseInt(urgent.value, 10) || 0 : 0;
  const backlog = dashboardTodoItems(todos)
    .filter((item) => item.pending > 0 && item.route && canNavigate(item.route))
    .sort((left, right) => right.pending - left.pending)
    .slice(0, urgentCount > 0 ? 2 : 3);
  return (
    <div className="wb-focus" role="group" aria-label="优先处理">
      <span className={`wb-focus-bell${urgentCount || backlog.length ? " is-ringing" : ""}`} aria-hidden="true"><BellFilled /></span>
      <span className="wb-focus-title">优先处理</span>
      {urgent && urgentCount > 0 && (
        <button type="button" className="wb-focus-chip is-urgent" onClick={() => onOpenMetric(urgent)}>
          <AlertOutlined aria-hidden="true" />紧急案件<b>{urgentCount}</b>
        </button>
      )}
      {backlog.map((item) => (
        <button
          type="button"
          key={item.label}
          className="wb-focus-chip"
          onClick={() => {
            prepareTodoNavigation(item.label);
            onNavigate(item.route!);
          }}
        >
          <span aria-hidden="true">{item.icon}</span>{item.label}<b>{item.pending}</b>
        </button>
      ))}
      {!urgentCount && !backlog.length && <span className="wb-focus-clear"><CheckCircleFilled aria-hidden="true" />暂无积压的待办</span>}
    </div>
  );
}
