import type { ReactNode } from "react";
import { Button, Empty, Tooltip } from "antd";
import { AuditOutlined, BankOutlined, CheckSquareOutlined, FileSearchOutlined, FolderOpenOutlined, ReloadOutlined, RightOutlined } from "@ant-design/icons";
import type { DashboardData } from "./dashboardData";
import DashboardGreeting from "./DashboardGreeting";

// 沿用工作台原有待办入口；统计展示与个人智能体对话互相独立。
const todoRoutes: Record<string, string> = {
  待处理任务: "task-my-accepted",
  待审批官方费用: "finance-payment-audit",
  待审批线索: "clue-audit-pending",
  待审批内部费用: "finance-internal-fee-audit",
  待审批合同: "contract-audit-pending",
  待审批结算费用: "finance-settlement-audit",
  待审批用印: "seal-audit-pending",
  待归档费用: "finance-archive-fee-pending",
  待审核归档: "case-archive-pending",
  // 控制台数字口径 Q2(a)：预损对应归档“亏损内审”案件，首页数字即该标签总数。
  待审核预损费用: "case-archive-loss-internal",
};

const todoIcons: Record<string, ReactNode> = {
  "task-my-accepted": <CheckSquareOutlined />,
  "clue-audit-pending": <FileSearchOutlined />,
  "contract-audit-pending": <AuditOutlined />,
  "seal-audit-pending": <AuditOutlined />,
  "case-archive-pending": <FolderOpenOutlined />,
  "case-archive-loss-internal": <FolderOpenOutlined />,
  "finance-payment-audit": <BankOutlined />,
  "finance-internal-fee-audit": <BankOutlined />,
  "finance-settlement-audit": <BankOutlined />,
  "finance-archive-fee-pending": <BankOutlined />,
};

type Props = {
  greeting: string;
  name?: string;
  briefing: ReactNode;
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

export default function DashboardOverview({ greeting, name, briefing, todos, cases, todoStatus, caseStatus, todosLoading, casesLoading, todosError, casesError, canNavigate, canOpenCase, onNavigate, onOpenCase, onRefresh }: Props) {
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
    <section className="wb-overview" aria-label="工作概况">
      <header className="wb-overview-head">
        <DashboardGreeting greeting={greeting} name={name} briefing={briefing} />
        <Tooltip title="刷新工作概况">
          <Button type="text" icon={<ReloadOutlined />} aria-label="刷新工作概况" onClick={onRefresh} />
        </Tooltip>
      </header>
      <div className="wb-overview-body">
        <section className="wb-overview-section" aria-label="我的待办">
          <div className="wb-overview-section-head">
            <h3>我的待办</h3>
            <span>任务、审批与归档</span>
          </div>
          {todoStatus}
          {!todosLoading && !todosError && !items.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待办事项" />}
          <div className="wb-todo-grid">
            {items.map(({ label, count }) => {
              const route = todoRoutes[label];
              const clickable = Boolean(route && canNavigate(route));
              const category = route?.startsWith("finance-") ? "finance" : route?.startsWith("case-archive-") ? "archive" : "workflow";
              const className = `wb-todo-entry todo-${category}${Number(count) > 0 ? " has-pending" : ""}`;
              const content = <>
                <span className="wb-todo-label"><span className="wb-todo-icon" aria-hidden="true">{todoIcons[route]}</span><span className="wb-todo-title">{label}</span></span>
                <span className="wb-todo-value"><strong>{count}</strong>{clickable && <RightOutlined aria-hidden="true" />}</span>
              </>;
              return clickable
                ? <button key={label} className={className} type="button" onClick={() => openTodo(label)}>{content}</button>
                : <div key={label} className={className}>{content}</div>;
            })}
          </div>
        </section>
        <section className="wb-overview-section wb-overview-recent" aria-label="最新案件">
          <div className="wb-overview-section-head">
            <h3>最新案件</h3>
            {!!cases?.length && <span>最近 {cases.length} 条</span>}
          </div>
          {caseStatus}
          {!casesLoading && !casesError && !cases?.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无案件" />}
          {!!cases?.length && <div className="wb-overview-case-list">
            <table className="wb-overview-cases">
              <caption className="wb-visually-hidden">最新案件的案号、当事人、案件阶段和创建日期</caption>
              <thead><tr><th scope="col">案号</th><th scope="col">当事人</th><th scope="col">案件阶段</th><th scope="col">创建日期</th></tr></thead>
              <tbody>{cases.map((item) => (
                <tr key={item.case_no}>
                  <td className="wb-overview-case-number">
                    {canOpenCase
                      ? <button type="button" onClick={() => onOpenCase(item.case_no)}>{item.case_no}</button>
                      : <span>{item.case_no}</span>}
                  </td>
                  <td className="wb-overview-parties"><span title={item.plaintiff}>{item.plaintiff}</span><span title={item.defendant}>{item.defendant}</span></td>
                  <td><span className="wb-overview-stage">{item.stage}</span></td>
                  <td className="wb-overview-case-date"><time>{item.date}</time></td>
                </tr>
              ))}</tbody>
            </table>
          </div>}
        </section>
      </div>
    </section>
  );
}
