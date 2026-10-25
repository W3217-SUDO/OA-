import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Button, Empty, Segmented, Tooltip } from "antd";
import { CheckCircleFilled, ReloadOutlined } from "@ant-design/icons";
import type { DashboardData, DashboardPortal } from "./dashboardData";
import DashboardGreeting from "./DashboardGreeting";
import { dashboardPortalItems, dashboardTodoItems, prepareTodoNavigation, type DashboardPortalTodoItem } from "./dashboardTodos";

const PORTAL_TAB_STORAGE = "sunhold:dashboard-portal";

// 待办格子按项数自动排列：一行放得下就平均铺满整行（至少按 4 列，避免一两项被拉得过宽），
// 放不下就按最少行数平均分配每行个数，不在最后一行留一大片空白。
function todoColumns(count: number, max: number) {
  if (count <= max) return Math.max(count, 4);
  return Math.ceil(count / Math.ceil(count / max));
}

// 一行最多放几格由待办区实际宽度决定：每格约 112px，最少 5 格、最多 10 格；手机宽度固定 5 格。
function maxTodoColumns(width: number) {
  if (width < 640) return 5;
  return Math.min(10, Math.max(5, Math.floor(width / 112)));
}

// 回调 ref：元素每次挂上（含重新渲染换了节点）都重新量宽度并监听变化。
function useElementWidth<T extends HTMLElement>() {
  const observer = useRef<ResizeObserver | null>(null);
  const [width, setWidth] = useState(0);
  const ref = useCallback((element: T | null) => {
    observer.current?.disconnect();
    observer.current = null;
    if (!element) return;
    setWidth(Math.round(element.getBoundingClientRect().width));
    if (typeof ResizeObserver === "undefined") return;
    observer.current = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)));
    observer.current.observe(element);
  }, []);
  useEffect(() => () => observer.current?.disconnect(), []);
  return [ref, width] as const;
}

function rememberedPortal() {
  try {
    return localStorage.getItem(PORTAL_TAB_STORAGE) || "";
  } catch {
    return "";
  }
}

type Props = {
  showHead?: boolean;
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
  // 首页分端待办：有端时按端分页签；没有端（角色未归属）时显示原来的“我的待办”。
  portals?: DashboardPortal[];
  portalData?: Partial<DashboardData>;
  portalsLoading?: boolean;
  onOpenMetric?: (metric: DashboardData["metrics"][number]) => void;
};

export default function DashboardOverview({ showHead = true, greeting, name, briefing, todos, cases, todoStatus, caseStatus, todosLoading, casesLoading, todosError, casesError, canNavigate, canOpenCase, onNavigate, onOpenCase, onRefresh, portals = [], portalData, portalsLoading = false, onOpenMetric }: Props) {
  const [portalKey, setPortalKey] = useState(rememberedPortal);
  const [gridRef, gridWidth] = useElementWidth<HTMLDivElement>();
  const activePortal = portals.find((portal) => portal.key === portalKey) || portals[0];
  const choosePortal = (key: string) => {
    setPortalKey(key);
    try {
      localStorage.setItem(PORTAL_TAB_STORAGE, key);
    } catch {
      // 浏览器禁用本地存储时只是不记住上次的页签。
    }
  };
  const items: (ReturnType<typeof dashboardTodoItems>[number] & Partial<DashboardPortalTodoItem>)[] =
    activePortal && portalData ? dashboardPortalItems(activePortal, portalData) : dashboardTodoItems(todos);
  const pendingItems = items.filter((item) => item.pending > 0);
  const pendingTotal = pendingItems.reduce((total, item) => total + (item.amount ? 0 : item.pending), 0);
  const loaded = !todosLoading && !todosError && !portalsLoading && items.length > 0;
  const openTodo = (label: string, route?: string, metric?: DashboardData["metrics"][number]) => {
    if (!route || !canNavigate(route)) return;
    if (metric && onOpenMetric) {
      onOpenMetric(metric);
      return;
    }
    prepareTodoNavigation(label);
    onNavigate(route);
  };
  return (
    <section className="wb-overview" aria-label="工作概况">
      {showHead && <header className="wb-overview-head">
        <DashboardGreeting greeting={greeting} name={name} briefing={briefing} />
        <Tooltip title="刷新工作概况">
          <Button type="text" icon={<ReloadOutlined />} aria-label="刷新工作概况" onClick={onRefresh} />
        </Tooltip>
      </header>}
      <div className="wb-overview-body">
        <section className="wb-overview-section" aria-label="我的待办">
          <div className="wb-overview-section-head">
            <h3>我的待办</h3>
            {portals.length > 1 && activePortal && <Segmented
              className="wb-portal-tabs"
              size="small"
              value={activePortal.key}
              options={portals.map((portal) => ({ label: portal.name, value: portal.key }))}
              onChange={(value) => choosePortal(String(value))}
            />}
            {loaded && (pendingItems.length
              ? <span className="wb-todo-summary is-pending"><i aria-hidden="true" />{pendingItems.length} 项待处理 · 共 {pendingTotal} 件</span>
              : <span className="wb-todo-summary is-clear"><CheckCircleFilled aria-hidden="true" />待办已全部处理</span>)}
          </div>
          {todoStatus}
          {!todosLoading && !todosError && !items.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待办事项" />}
          {/* 图标宫格（类似钉钉工作台）：统一用主题色，有待办的图标填满并在右上角挂角标写件数，没有待办的只是浅色描边。 */}
          <div ref={gridRef} className="wb-todo-grid" style={{ "--todo-cols": todoColumns(items.length, gridWidth ? maxTodoColumns(gridWidth) : 5) } as CSSProperties}>
            {items.map(({ label, count, pending, route, icon, metric, description: itemDescription }) => {
              const clickable = Boolean(route && canNavigate(route));
              const className = `wb-todo-entry${pending > 0 ? " has-pending" : " is-clear"}`;
              const content = <>
                <span className="wb-todo-icon" aria-hidden="true">
                  {icon}
                  {pending > 0 && <i className="wb-todo-badge">{count}</i>}
                </span>
                <span className="wb-todo-title">{label}</span>
              </>;
              const description = pending > 0 ? `${label}，${count} 件待处理` : `${label}，暂无待办`;
              return clickable
                ? <button key={label} className={className} type="button" title={itemDescription} onClick={() => openTodo(label, route, metric)} aria-label={description}>{content}</button>
                : <div key={label} className={className} title={itemDescription} aria-label={description}>{content}</div>;
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
          {/* 与原系统“最新案件”同样的字段，全部显示：宽屏逐列；卡片较窄时原告/被告合成一列、开庭/经办/助理合成一列（带小标签），信息不减少。人名全部列出，不截断。 */}
          {!!cases?.length && <div className="wb-overview-case-list">
            <table className="wb-overview-cases">
              <caption className="wb-visually-hidden">最新案件的案号、阶段、原告、被告、案源日期、客户管理人、开庭律师、经办律师和律师助理</caption>
              <thead><tr>
                <th scope="col" className="case-col-no">案号</th>
                <th scope="col" className="case-col-stage">阶段</th>
                <th scope="col" className="case-wide case-col-party">原告</th>
                <th scope="col" className="case-wide case-col-party">被告</th>
                <th scope="col" className="case-narrow">原告 / 被告</th>
                <th scope="col" className="case-col-date">案源日期</th>
                <th scope="col" className="case-col-person">客户管理人</th>
                <th scope="col" className="case-wide case-col-person">开庭律师</th>
                <th scope="col" className="case-wide case-col-person">经办律师</th>
                <th scope="col" className="case-wide case-col-person">律师助理</th>
                <th scope="col" className="case-narrow case-col-team">承办律师</th>
              </tr></thead>
              <tbody>{cases.map((item) => (
                <tr key={item.case_no}>
                  <td className="wb-overview-case-number">
                    {canOpenCase
                      ? <button type="button" onClick={() => onOpenCase(item.case_no)}>{item.case_no}</button>
                      : <span>{item.case_no}</span>}
                  </td>
                  <td className="wb-overview-case-stage"><span className="wb-overview-stage">{item.stage || "—"}</span></td>
                  <td className="case-wide">{item.plaintiff || "—"}</td>
                  <td className="case-wide">{item.defendant || "—"}</td>
                  <td className="case-narrow wb-overview-parties">
                    <span><i>原告</i>{item.plaintiff || "—"}</span>
                    <span><i>被告</i>{item.defendant || "—"}</span>
                  </td>
                  <td className="wb-overview-case-date"><time>{item.date || "—"}</time></td>
                  <td className="wb-overview-case-manager">{item.manager || "—"}</td>
                  <td className="case-wide">{item.lawyer || "—"}</td>
                  <td className="case-wide">{item.agent || "—"}</td>
                  <td className="case-wide">{item.assistant || "—"}</td>
                  <td className="case-narrow wb-overview-team">
                    <span><i>开庭</i>{item.lawyer || "—"}</span>
                    <span><i>经办</i>{item.agent || "—"}</span>
                    <span><i>助理</i>{item.assistant || "—"}</span>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>}
        </section>
      </div>
    </section>
  );
}
