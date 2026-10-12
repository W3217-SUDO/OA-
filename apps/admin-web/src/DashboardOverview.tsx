import type { ReactNode } from "react";
import { Button, Empty } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import type { DashboardData } from "./dashboardData";

// 沿用工作台原有待办入口；统计展示与个人智能体对话互相独立。
const todoRoutes: Record<string, string> = {
  待处理任务: "task-my-accepted",
  待审批官方费用: "finance-payment-audit",
  待审批线索: "clue-audit-pending",
  待审批内部费用: "finance-internal-fee-audit",
  待审批合同: "contract-audit-pending",
  待审批结算费用: "finance-settlement-audit",
  待审批用印: "seal-audit-pending",
  待审批归档费用: "finance-archive-fee-pending",
  待审核归档: "case-archive-pending",
  待审核预损费用: "finance-internal-fee-audit",
};

type Props = {
  todos?: DashboardData["todos"];
  cases?: DashboardData["latest_cases"];
  todoStatus: ReactNode;
  caseStatus: ReactNode;
  todosLoading: boolean;
  casesLoading: boolean;
  todosError: boolean;
  casesError: boolean;
  canNavigate: (route: string) => boolean;
  canOpenCase: boolean;
  onNavigate: (route: string) => void;
  onOpenCase: (caseNo: string) => void;
  onRefresh: () => void;
};

export default function DashboardOverview({ todos, cases, todoStatus, caseStatus, todosLoading, casesLoading, todosError, casesError, canNavigate, canOpenCase, onNavigate, onOpenCase, onRefresh }: Props) {
  const items = (todos || []).flatMap((row) => [
    { label: String(row[0]), count: row[1] },
    { label: String(row[3]), count: row[4] },
  ]);
  const openTodo = (label: string) => {
    const route = todoRoutes[label];
    if (!route || !canNavigate(route)) return;
    if (label === "待处理任务") sessionStorage.setItem("sunhold:dashboard-task-tab", "pending");
    onNavigate(route);
  };
  return (
    <section className="wb-overview" aria-label="工作概览">
      <header className="wb-overview-head">
        {/* 问候语由顶部提醒指标那一行统一展示，这里只保留刷新入口，避免重复。 */}
        <Button icon={<ReloadOutlined />} onClick={onRefresh}>刷新概览</Button>
      </header>
      <div className="wb-overview-body">
        <section className="wb-overview-section" aria-label="我的待办">
          <h3>我的待办</h3>
          {todoStatus}
          {!todosLoading && !todosError && !items.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待办事项" />}
          <div className="wb-todo-grid">
            {items.map(({ label, count }) => {
              const route = todoRoutes[label];
              const content = <><span>{label}</span><strong>{count}</strong></>;
              return route && canNavigate(route)
                ? <button key={label} className="wb-todo-entry" type="button" onClick={() => openTodo(label)}>{content}</button>
                : <div key={label} className="wb-todo-entry">{content}</div>;
            })}
          </div>
        </section>
        <section className="wb-overview-section" aria-label="最新案件">
          <h3>最新案件</h3>
          {caseStatus}
          {!casesLoading && !casesError && !cases?.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无案件" />}
          {!!cases?.length && <ul className="wb-overview-cases">
            {cases.map((item) => (
              <li key={item.case_no}>
                <div className="wb-overview-case-head">
                  {canOpenCase
                    ? <button type="button" onClick={() => onOpenCase(item.case_no)}>{item.case_no}</button>
                    : <span>{item.case_no}</span>}
                  <span>{item.stage}</span>
                  <time>{item.date}</time>
                </div>
                <p>{item.plaintiff} / {item.defendant}</p>
              </li>
            ))}
          </ul>}
        </section>
      </div>
    </section>
  );
}
