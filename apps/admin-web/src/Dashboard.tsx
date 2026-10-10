import { useCallback, useEffect, useMemo, useRef, type KeyboardEvent } from "react";
import { Button, Card, message } from "antd";
import Table from "./components/ResizableTable";
import DashboardPersonCell from "./DashboardPersonCell";
import { useDashboardData, type DashboardData, type DashboardSection } from "./dashboardData";
import { rememberDashboardFeeQuery } from "./dashboardFeeNavigation.mjs";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import { resolveDetailRelation } from "./detailRelationResolver";
import { isWorkspaceRouteGranted, normalizeWorkspaceRoute } from "./workspacePermissions";

function CaseTrendChart({
  items,
}: {
  items: { date: string; value: number }[];
}) {
  const width = 470,
    height = 220,
    left = 38,
    right = 12,
    top = 12,
    bottom = 52,
    plotWidth = width - left - right,
    plotHeight = height - top - bottom,
    maxValue = Math.max(1, ...items.map((item) => item.value)),
    max = Math.max(5, Math.ceil(maxValue / 5) * 5),
    ticks = Array.from({ length: 5 }, (_, index) => Math.round((max * index) / 4));
  const points = items
    .map(
      (item, index) =>
        `${left + (items.length === 1 ? 0 : (index * plotWidth) / (items.length - 1))},${top + plotHeight - (item.value / max) * plotHeight}`,
    )
    .join(" ");
  return (
    <svg
      className="case-trend-chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="案件趋势折线图"
    >
      {ticks.map((value) => {
        const y = top + plotHeight - (value / max) * plotHeight;
        return (
          <g key={value}>
            <line
              x1={left}
              y1={y}
              x2={width - right}
              y2={y}
              className="trend-grid-line"
            />
            <text
              x={left - 8}
              y={y + 4}
              textAnchor="end"
              className="trend-axis-text"
            >
              {value}
            </text>
          </g>
        );
      })}
      {items.map((item, index) => {
        const x =
          left +
          (items.length === 1 ? 0 : (index * plotWidth) / (items.length - 1));
        return (
          <line
            key={item.date}
            x1={x}
            y1={top}
            x2={x}
            y2={top + plotHeight}
            className="trend-grid-line vertical"
          />
        );
      })}
      <polyline points={points} className="trend-line" />
      {items.map((item, index) => {
        const x =
            left +
            (items.length === 1 ? 0 : (index * plotWidth) / (items.length - 1)),
          y = top + plotHeight - (item.value / max) * plotHeight;
        return (
          <g key={`${item.date}-point`}>
            <circle cx={x} cy={y} r="3.5" className="trend-point" />
            <text
              transform={`translate(${x - 2} ${height - 38}) rotate(-45)`}
              textAnchor="end"
              className="trend-date-text"
            >
              {item.date}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function CivilDistribution({
  items,
}: {
  items: { label: string; value: number; color: string }[];
}) {
  const total = items.reduce((sum, item) => sum + item.value, 0) || 1;
  let cursor = 0;
  const gradient = items
    .map((item) => {
      const start = (cursor / total) * 360;
      cursor += item.value;
      const end = (cursor / total) * 360;
      return `${item.color} ${start}deg ${end}deg`;
    })
    .join(",");
  return (
    <div className="civil-distribution">
      <div
        className="donut-chart"
        style={{ background: `conic-gradient(${gradient})` }}
      >
        <div className="donut-hole" />
      </div>
      <div className="donut-legend">
        {items.map((item) => (
          <span key={item.label}>
            <i style={{ background: item.color }} />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function Dashboard({ onNavigate, grantedMenuKeys, permissionAdministrator }: {
  onNavigate: (route: string) => void;
  grantedMenuKeys: ReadonlySet<string>;
  permissionAdministrator: boolean;
}) {
  const { data, loading, errors, retry } = useDashboardData();
  const detailRequest = useRef<AbortController | null>(null);
  const navigation = useRef({ onNavigate, grantedMenuKeys, permissionAdministrator });
  navigation.current = { onNavigate, grantedMenuKeys, permissionAdministrator };
  useEffect(() => () => detailRequest.current?.abort(), []);
  const canNavigate = (route: string) => isWorkspaceRouteGranted(
    normalizeWorkspaceRoute(route), grantedMenuKeys, permissionAdministrator,
  );
  const canOpenCase = canNavigate("case-detail-");
  const canOpenCustomer = canNavigate("customer-detail-");
  const sectionStatus = (section: DashboardSection) => errors[section]
    ? <div className="dashboard-section-status" role="alert">{errors[section]} <Button size="small" onClick={() => retry(section)}>重试</Button></div>
    : loading[section] ? <div className="dashboard-section-status" role="status">正在加载...</div> : null;
  const todoRoutes: Record<string, { primary: string; secondary: string }> = {
    待处理任务: { primary: "task-my-accepted", secondary: "task-my-created" },
    待审批官方费用: { primary: "finance-payment-audit", secondary: "finance-payment-audit" },
    待审批线索: { primary: "clue-audit-pending", secondary: "clue-audit-refused" },
    待审批内部费用: { primary: "finance-internal-fee-audit", secondary: "finance-internal-fee-audit" },
    待审批合同: { primary: "contract-audit-pending", secondary: "contract-audit-refused" },
    待审批结算费用: { primary: "finance-settlement-audit", secondary: "finance-settlement-audit" },
    待审批用印: { primary: "seal-audit-pending", secondary: "seal-my-refused" },
    待审批归档费用: { primary: "finance-archive-fee-pending", secondary: "finance-archive-fee-pending" },
    待审核归档: { primary: "case-archive-pending", secondary: "case-archive-refused" },
    待审核预损费用: { primary: "finance-internal-fee-audit", secondary: "finance-internal-fee-audit" },
  };
  const navigateTodo = (label: string, kind: "primary" | "secondary") => {
    const route = todoRoutes[label]?.[kind];
    if (!route || !canNavigate(route)) return;
    if (label === "待处理任务") {
      sessionStorage.setItem(
        "sunhold:dashboard-task-tab",
        kind === "secondary" ? "rejected" : "pending",
      );
    }
    onNavigate(route);
  };
  const renderTodoEntry = (value: string | number, label: string, kind: "primary" | "secondary", className: string, ariaLabel?: string) => {
    const route = todoRoutes[label]?.[kind];
    return route && canNavigate(route) ? (
      <button
        type="button"
        className={className}
        aria-label={ariaLabel}
        title={typeof value === "number" ? (kind === "primary" ? "查看待处理列表" : "查看已拒绝列表") : undefined}
        onClick={() => navigateTodo(label, kind)}
      >{value}</button>
    ) : <span className={className} style={{ cursor: "default", textDecoration: "none", color: "inherit" }}>{value}</span>;
  };
  const navigateMetric = (metric: DashboardData["metrics"][number]) => {
    if (!canNavigate(metric.route)) return;
    rememberDashboardFeeQuery(metric.query);
    if (metric.detail_context) {
      try {
        sessionStorage.setItem("sunhold:receivable-detail-context", JSON.stringify(metric.detail_context));
      } catch {
        // Navigation still works when the browser blocks session storage.
      }
    }
    onNavigate(metric.route);
  };
  const keyboardNavigate = (
    event: KeyboardEvent,
    metric: DashboardData["metrics"][number],
  ) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      navigateMetric(metric);
    }
  };
  const openDashboardDetail = useCallback(async (module: "case" | "customer", value: string) => {
    detailRequest.current?.abort();
    const controller = new AbortController();
    detailRequest.current = controller;
    try {
      // 先按现有数据范围解析真实记录，再进入详情，不借用公司列表的页面授权。
      const record = await resolveDetailRelation(module, module === "case" ? { serial_no: value } : { title: value }, controller.signal);
      if (controller.signal.aborted) return;
      if (!record) {
        message.warning(module === "case" ? "未找到关联案件或当前账号无权查看" : "未找到关联客户或当前账号无权查看");
        return;
      }
      const detailLabel = module === "case" ? record.serial_no : record.title;
      const route = `${module}-detail-${record.id}-${encodeURIComponent(detailLabel)}`;
      const current = navigation.current;
      if (!isWorkspaceRouteGranted(route, current.grantedMenuKeys, current.permissionAdministrator)) return;
      if (module === "case") rememberCaseDetailTarget({ id: record.id, serial_no: record.serial_no });
      else rememberCustomerDetailTarget({ id: record.id, title: record.title, serial_no: record.serial_no });
      current.onNavigate(route);
    } catch (error: any) {
      if (!controller.signal.aborted) message.error(error?.response?.data?.detail || (module === "case" ? "关联案件加载失败" : "关联客户加载失败"));
    }
  }, []);
  const hearingCols = useMemo(
    () => [
      { title: "星期", dataIndex: "weekday", width: 80 },
      { title: "日期", dataIndex: "date", width: 100 },
      { title: "时间", dataIndex: "time", width: 90 },
      { title: "开庭法院", dataIndex: "court", ellipsis: true },
      {
        title: "案号",
        dataIndex: "case_no",
        width: 140,
        render: (v: string) => canOpenCase ? <a onClick={() => void openDashboardDetail("case", v)}>{v}</a> : v,
      },
      {
        title: "客户",
        dataIndex: "client",
        ellipsis: true,
        render: (value: string) =>
          value ? canOpenCustomer ? <a onClick={() => void openDashboardDetail("customer", value)}>{value}</a> : value : "—",
      },
      {
        title: "开庭律师",
        dataIndex: "lawyer",
        width: 105,
        ellipsis: true,
        render: (value: string) => <DashboardPersonCell value={value} />,
      },
      {
        title: "经办律师",
        dataIndex: "agent",
        width: 115,
        ellipsis: true,
        render: (value: string) => <DashboardPersonCell value={value} />,
      },
      { title: "律师助理", dataIndex: "assistant", width: 105, ellipsis: true, render: (value: string) => <DashboardPersonCell value={value} /> },
    ],
    [canOpenCase, canOpenCustomer, openDashboardDetail],
  );
  const latestCaseCols = useMemo(
    () => [
      {
        title: "案号",
        dataIndex: "case_no",
        width: 125,
        render: (v: string) => canOpenCase ? <a onClick={() => void openDashboardDetail("case", v)}>{v}</a> : v,
      },
      { title: "阶段", dataIndex: "stage", width: 100 },
      { title: "原告", dataIndex: "plaintiff", width: 185, ellipsis: true },
      { title: "被告", dataIndex: "defendant", width: 205, ellipsis: true },
      { title: "案源日期", dataIndex: "date", width: 100 },
      { title: "客户管理人", dataIndex: "manager", width: 90, ellipsis: true, render: (value: string) => <DashboardPersonCell value={value} /> },
      { title: "开庭律师", dataIndex: "lawyer", width: 85, ellipsis: true, render: (value: string) => <DashboardPersonCell value={value} /> },
      { title: "经办律师", dataIndex: "agent", width: 100, ellipsis: true, render: (value: string) => <DashboardPersonCell value={value} /> },
      { title: "律师助理", dataIndex: "assistant", width: 85, ellipsis: true, render: (value: string) => <DashboardPersonCell value={value} /> },
    ],
    [canOpenCase, openDashboardDetail],
  );
  return (
    <div className="reference-dashboard">
      <div className="dashboard-legacy-grid">
        <div className="dashboard-metrics-panel">
          {sectionStatus("metrics")}
          <div className="metrics reference-metrics">
          {data.metrics?.map((m, i) => {
            const allowed = canNavigate(m.route);
            return (
              <div
                className={`metric target-${i}`}
                key={m.key}
                role={allowed ? "button" : undefined}
                tabIndex={allowed ? 0 : undefined}
                style={allowed ? undefined : { cursor: "default", filter: "none", outline: "none" }}
                onClick={allowed ? () => navigateMetric(m) : undefined}
                onKeyDown={allowed ? (event) => keyboardNavigate(event, m) : undefined}
              >
                <div className="metric-icon">
                  {["◷", "✉", "♟", "⚖", "⚑", "▤", "☕", "¥"][i]}
                </div>
                <div>
                  <strong>{m.value}</strong>
                  <span>{m.label}</span>
                </div>
              </div>
            );
          })}
          </div>
        </div>
        <Card title="➤ 待办事项" className="dashboard-card compact-todo-card">
          {sectionStatus("todos")}
          <table className="todo-table">
            <tbody>
              {data.todos?.map((row, i) => (
                <tr key={i}>
                  {row.map((c, j) => {
                    const label = String(row[j < 3 ? 0 : 3]);
                    const kind = j % 3 === 2 ? "secondary" : "primary";
                    return (
                      <td
                        key={j}
                        className={
                          typeof c === "number" ? `count count-${j % 3}` : ""
                        }
                      >
                        {renderTodoEntry(c, label, kind, "todo-link")}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mobile-todo-list">
            {data.todos?.flatMap((row, rowIndex) =>
              [
                { label: row[0], primary: row[1], secondary: row[2] },
                { label: row[3], primary: row[4], secondary: row[5] },
              ].map((item, itemIndex) => {
                return (
                  <div
                    className="mobile-todo-item"
                    key={`${rowIndex}-${itemIndex}`}
                  >
                    {renderTodoEntry(item.label, String(item.label), "primary", "mobile-todo-label")}
                    {renderTodoEntry(item.primary, String(item.label), "primary", "mobile-todo-count primary", `${item.label}待处理`)}
                    {renderTodoEntry(item.secondary, String(item.label), "secondary", "mobile-todo-count secondary", `${item.label}已拒绝`)}
                  </div>
                );
              }),
            )}
          </div>
        </Card>
        <Card title={canNavigate("case-mine-schedule") ? <Button type="link" style={{ padding: 0, color: "inherit", fontSize: "inherit", fontWeight: "inherit" }} onClick={() => onNavigate("case-mine-schedule")}>开庭排期</Button> : "开庭排期"} className="dashboard-card target-hearing-card">
          {sectionStatus("cases")}
          <Table
            rowKey={(r) => `${r.case_no}-${r.time}`}
            size="small"
            pagination={false}
            columns={hearingCols}
            dataSource={data.hearings}
            loading={loading.cases}
            scroll={{ x: 1050, y: 180 }}
            sticky={false}
          />
        </Card>
        <Card title="◩ 案件趋势" className="dashboard-card target-trend-card">
          {data.case_trend ? <CaseTrendChart items={data.case_trend} /> : sectionStatus("cases")}
        </Card>
        <Card title="◉ 最新案件" className="dashboard-card latest-cases-card">
          <Table
            rowKey="case_no"
            size="small"
            pagination={false}
            columns={latestCaseCols}
            dataSource={data.latest_cases}
            loading={loading.cases}
            scroll={{ x: 1100, y: 300 }}
            sticky={false}
          />
        </Card>
        <Card title="◔ 民事案件" className="dashboard-card civil-card">
          {data.civil_distribution ? <CivilDistribution items={data.civil_distribution} /> : sectionStatus("cases")}
        </Card>
      </div>
    </div>
  );
}
