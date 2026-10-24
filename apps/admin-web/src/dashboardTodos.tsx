import type { ReactNode } from "react";
import {
  BankOutlined,
  CalculatorOutlined,
  CheckSquareOutlined,
  ContainerOutlined,
  FallOutlined,
  FileProtectOutlined,
  FileSearchOutlined,
  FolderOpenOutlined,
  SafetyCertificateOutlined,
  WalletOutlined,
} from "@ant-design/icons";
import type { DashboardData } from "./dashboardData";

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

// “待处理任务”进入任务中心时直接打开“待处理”标签页。
export function prepareTodoNavigation(label: string) {
  if (label !== "待处理任务") return;
  try {
    sessionStorage.setItem("sunhold:dashboard-task-tab", "pending");
  } catch {
    // 浏览器禁用会话存储时仍然跳转，只是停在默认标签页。
  }
}
