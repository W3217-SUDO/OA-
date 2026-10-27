import type { ReactNode } from "react";
import {
  AlertOutlined,
  AuditOutlined,
  BankOutlined,
  CalculatorOutlined,
  CheckCircleOutlined,
  CheckSquareOutlined,
  ContainerOutlined,
  DollarOutlined,
  FallOutlined,
  FileAddOutlined,
  FileDoneOutlined,
  FileProtectOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
  MessageOutlined,
  PayCircleOutlined,
  RiseOutlined,
  RollbackOutlined,
  SafetyCertificateOutlined,
  ScheduleOutlined,
  TransactionOutlined,
  WalletOutlined,
} from "@ant-design/icons";
import type { DashboardData, DashboardPortal } from "./dashboardData";
import { rememberFeedbackStatusFilter } from "./feedback/navigation";

// 工作台“我的待办”的入口和图标，顺序和入口沿用原有待办。
export const DASHBOARD_TODOS: Record<string, { route: string; icon: ReactNode }> = {
  待处理任务: { route: "task-my-accepted", icon: <CheckSquareOutlined /> },
  待审批官方费用: { route: "finance-payment-audit", icon: <BankOutlined /> },
  待审批线索: { route: "clue-audit-pending", icon: <FileSearchOutlined /> },
  待审批内部费用: { route: "finance-internal-fee-audit", icon: <WalletOutlined /> },
  待审批合同: { route: "contract-audit-pending", icon: <FileProtectOutlined /> },
  待审批结算费用: { route: "finance-settlement-audit", icon: <CalculatorOutlined /> },
  待审批用印: { route: "seal-audit-pending", icon: <SafetyCertificateOutlined /> },
  待归档费用: { route: "finance-archive-fee-pending", icon: <ContainerOutlined /> },
  // 1.1.548 之前接口返回的旧名称，同一入口。
  待审批归档费用: { route: "finance-archive-fee-pending", icon: <ContainerOutlined /> },
  待审核归档: { route: "case-archive-pending", icon: <FolderOpenOutlined /> },
  // 控制台数字口径 Q2(a)：预损对应归档“亏损内审”案件，首页数字即该标签总数。
  待审核预损费用: { route: "case-archive-loss-internal", icon: <FallOutlined /> },
};

export type DashboardTodoItem = { label: string; count: string | number; pending: number; route?: string; icon?: ReactNode };

// 后端每行返回两组“名称、数量”，按原顺序展开成一项一格。
export function dashboardTodoItems(todos: DashboardData["todos"] | undefined): DashboardTodoItem[] {
  return (todos || []).flatMap((row) => [
    { label: String(row[0]), count: row[1] },
    { label: String(row[3]), count: row[4] },
  ]).map(({ label, count }) => {
    const meta = DASHBOARD_TODOS[label];
    return { label, count, pending: Number(count) || 0, route: meta?.route, icon: meta?.icon };
  });
}

// 管理端两项进入问题处理中心时按状态筛选。
const FEEDBACK_TODO_STATUS: Record<string, string> = { 问题反馈: "待处理", 问题处理中心: "待验证" };

// “待处理任务”进入任务中心时直接打开“待处理”标签页。
export function prepareTodoNavigation(label: string) {
  if (FEEDBACK_TODO_STATUS[label]) {
    rememberFeedbackStatusFilter(FEEDBACK_TODO_STATUS[label]);
    return;
  }
  if (label !== "待处理任务") return;
  try {
    sessionStorage.setItem("sunhold:dashboard-task-tab", "pending");
  } catch {
    // 浏览器禁用会话存储时仍然跳转，只是停在默认标签页。
  }
}

// 首页分端待办：目录项的图标；数字来源见后端 dashboard_portals.PORTAL_ITEMS（todo/metric 复用已有统计，extra 单独统计）。
const PORTAL_ICONS: Record<string, ReactNode> = {
  "fee-unpaid": <PayCircleOutlined />,
  "fee-audit": <BankOutlined />,
  "archive-fee": <ContainerOutlined />,
  "seal-stamping": <SafetyCertificateOutlined />,
  appeal: <RiseOutlined />,
  evidence: <FileAddOutlined />,
  opinion: <FileTextOutlined />,
  "receipts-pending": <TransactionOutlined />,
  receivable: <DollarOutlined />,
  "archive-closing": <FileDoneOutlined />,
  "notary-review": <AuditOutlined />,
  execution: <ScheduleOutlined />,
  urgent: <AlertOutlined />,
  refund: <RollbackOutlined />,
  "fee-unreceived": <WalletOutlined />,
  "feedback-pending": <MessageOutlined />,
  "feedback-verify": <CheckCircleOutlined />,
};

export type DashboardPortalTodoItem = DashboardTodoItem & { key: string; description: string; metric?: DashboardData["metrics"][number]; amount?: boolean };

// 一个端的待办格子：数字取自“我的待办”、提醒指标或分端单独统计，与点进去的列表同一口径。
export function dashboardPortalItems(portal: DashboardPortal, data: Partial<DashboardData>): DashboardPortalTodoItem[] {
  const catalog = new Map((data.portal_items || []).map((item) => [item.key, item]));
  const todos = new Map(dashboardTodoItems(data.todos).map((item) => [item.label, item]));
  const metrics = new Map((data.metrics || []).map((metric) => [metric.key, metric]));
  return portal.items.flatMap((key) => {
    const item = catalog.get(key);
    if (!item) return [];
    const [kind, ref] = item.source.split(":");
    const base = { key, label: item.label, description: item.description, route: item.route, icon: PORTAL_ICONS[key] };
    if (kind === "todo") {
      const todo = todos.get(ref);
      return [{ ...base, icon: todo?.icon || base.icon, count: todo?.count ?? 0, pending: todo?.pending ?? 0 }];
    }
    if (kind === "metric") {
      const metric = metrics.get(ref);
      const value = metric?.value || "0";
      const pending = Number.parseFloat(value) || 0;
      // 件数只显示数字；金额（未到官费）保留“元”，不计入“共 N 件”。
      const amount = value.endsWith("元");
      const count = value.endsWith("件") ? value.slice(0, -1) : value;
      return [{ ...base, route: metric?.route || item.route, metric, count, pending, amount }];
    }
    const count = data.portal_counts?.[key] ?? 0;
    return [{ ...base, count, pending: count }];
  });
}
