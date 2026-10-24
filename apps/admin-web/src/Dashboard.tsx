import { useCallback, useEffect, useRef } from "react";
import { Button, message } from "antd";
import dayjs from "dayjs";
import AssistantPanel, { type AssistantSuggestion } from "./personal-agent/AssistantPanel";
import { usePersonalWorkspaceContext } from "./personal-agent/PersonalWorkspaceProvider";
import DashboardHearingSchedule from "./DashboardHearingSchedule";
import DashboardMetricTiles from "./DashboardMetricTiles";
import DashboardRejectionReminder from "./DashboardRejectionReminder";
import DashboardOverview from "./DashboardOverview";
import DashboardGreeting from "./DashboardGreeting";
import { useDashboardData, type DashboardData, type DashboardRejection, type DashboardSection } from "./dashboardData";
import { rejectionsPrompt, todayHearingsPrompt } from "./dashboardPrompts";
import { rememberDashboardFeeQuery } from "./dashboardFeeNavigation.mjs";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import { resolveDetailRelation } from "./detailRelationResolver";
import { isWorkspaceRouteGranted, normalizeWorkspaceRoute } from "./workspacePermissions";

const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

export type DashboardView = "overview" | "conversation";

function greetingByHour(hour: number) {
  if (hour < 6) return "凌晨好";
  if (hour < 12) return "上午好";
  if (hour < 14) return "中午好";
  if (hour < 18) return "下午好";
  return "晚上好";
}

export default function Dashboard({
  view,
  isNarrowViewport,
  onViewChange,
  onNavigate,
  grantedMenuKeys,
  permissionAdministrator,
  assistantFocusRequested,
  onAssistantFocusHandled,
}: {
  view: DashboardView;
  isNarrowViewport: boolean;
  onViewChange: (view: DashboardView) => void;
  onNavigate: (route: string) => void;
  grantedMenuKeys: ReadonlySet<string>;
  permissionAdministrator: boolean;
  assistantFocusRequested: boolean;
  onAssistantFocusHandled: () => void;
}) {
  const { data, loading, errors, retry } = useDashboardData();
  // 运行时由路由外的容器持有，提醒切到独立 Ai 页面后仍保留当前对话和草稿。
  const workspace = usePersonalWorkspaceContext();
  const detailRequest = useRef<AbortController | null>(null);
  const navigation = useRef({ onNavigate, grantedMenuKeys, permissionAdministrator });
  navigation.current = { onNavigate, grantedMenuKeys, permissionAdministrator };
  useEffect(() => () => detailRequest.current?.abort(), []);
  useEffect(() => {
    if (isNarrowViewport && assistantFocusRequested && view !== "conversation") onViewChange("conversation");
  }, [isNarrowViewport, assistantFocusRequested, onViewChange, view]);
  const showEmbeddedConversation = isNarrowViewport && view === "conversation";
  const canNavigate = (route: string) => isWorkspaceRouteGranted(
    normalizeWorkspaceRoute(route), grantedMenuKeys, permissionAdministrator,
  );
  const canOpenCase = canNavigate("case-detail-");
  const canOpenCustomer = canNavigate("customer-detail-");
  const sectionStatus = (section: DashboardSection) => errors[section]
    ? <div className="dashboard-section-status" role="alert">{errors[section]} <Button size="small" onClick={() => retry(section)}>重试</Button></div>
    : loading[section] ? <div className="dashboard-section-status" role="status">正在加载...</div> : null;
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
  const openHearingAgent = useCallback(async (caseNo: string) => {
    if (!canOpenCase) return;
    detailRequest.current?.abort();
    const controller = new AbortController();
    detailRequest.current = controller;
    try {
      const record = await resolveDetailRelation("case", { serial_no: caseNo }, controller.signal);
      if (controller.signal.aborted) return;
      if (!record) {
        message.warning("未找到关联案件或当前账号无权查看");
        return;
      }
      const route = `case-detail-${record.id}-${encodeURIComponent(record.serial_no)}-agent-trial-prep`;
      const current = navigation.current;
      if (!isWorkspaceRouteGranted(route, current.grantedMenuKeys, current.permissionAdministrator)) return;
      rememberCaseDetailTarget({ id: record.id, serial_no: record.serial_no });
      current.onNavigate(route);
    } catch (error: any) {
      if (!controller.signal.aborted) message.error(error?.response?.data?.detail || "案件智能体加载失败");
    }
  }, [canOpenCase]);
  const openRejection = (item: DashboardRejection) => {
    // 被拒绝的任务在“我发起的任务”里按已拒绝标签页展示。
    if (item.route === "task-my-created") sessionStorage.setItem("sunhold:dashboard-task-tab", "rejected");
    onNavigate(item.route);
  };
  // 提醒里的“交给智能体”和输入框共用当前对话；当前对话忙碌时另开一条对话并行回答。
  const askAgent = (prompt: string) => {
    // 由父级按当前端设备切换到助手入口，继续复用同一工作区。
    onViewChange("conversation");
    if (workspace.loading || workspace.loadError || !workspace.status?.ready || workspace.conversationBusy || workspace.uploading || workspace.decisionId || workspace.stopping) {
      // 当前无法发送时保留完整问题，也不覆盖用户已输入的草稿。
      workspace.setInput((current) => current.trim() ? `${current}\n\n${prompt}` : prompt);
      return;
    }
    if (!workspace.sending) {
      void workspace.send(prompt);
      return;
    }
    void (async () => {
      try {
        const created = await workspace.createConversation();
        await workspace.send(prompt, created);
      } catch (error: any) {
        message.error(error?.response?.data?.detail || error?.message || "智能体暂时无法接受新的提醒");
      }
    })();
  };

  const now = dayjs();
  const todayHearings = (data.hearings || []).filter((item) => item.date === now.format("YYYY-MM-DD"));
  const rejections = data.rejections || [];
  const rejectionTotal = data.rejection_total || 0;
  // 根据今天的开庭和被驳回的审批生成建议，点击后把具体内容发给智能体。
  const suggestions: AssistantSuggestion[] = [];
  if (todayHearings.length) {
    // 后端按日期和时间排序，今天的第一条就是最早的一场。
    const first = todayHearings[0];
    suggestions.push({ kind: "hearing", label: "准备今天的开庭", hint: `最早 ${first.time} ${first.court || "法院待定"}`, count: todayHearings.length, prompt: todayHearingsPrompt(todayHearings) });
  }
  if (rejections.length) {
    suggestions.push({ kind: "rejection", label: "处理被驳回的审批", hint: `最近一条：${rejections[0].title}`, count: rejectionTotal, prompt: rejectionsPrompt(rejections, rejectionTotal) });
  }
  const briefing = errors.cases || errors.rejections
    ? "今天的数据没有加载完整，请使用下方的重试按钮"
    : loading.cases || loading.rejections
      ? "正在汇总今天的工作"
      : (
        <>
          {now.format("M月D日")}{WEEKDAYS[now.day()]}，
          {todayHearings.length ? <>今天有 <b className="is-hearing">{todayHearings.length}</b> 场开庭</> : "今天没有开庭"}，
          {rejectionTotal ? <><b className="is-rejection">{rejectionTotal}</b> 条审批被驳回</> : "没有被驳回的审批"}。
        </>
      );
  const schedule = (
    <DashboardHearingSchedule
      hearings={data.hearings || []}
      loading={loading.cases}
      status={sectionStatus("cases")}
      canOpenSchedule={canNavigate("case-mine-schedule")}
      canOpenCase={canOpenCase}
      canOpenCustomer={canOpenCustomer}
      onOpenSchedule={() => onNavigate("case-mine-schedule")}
      onOpenCase={(caseNo) => void openDashboardDetail("case", caseNo)}
      onOpenCustomer={(customer) => void openDashboardDetail("customer", customer)}
      onOpenHearingAgent={(caseNo) => void openHearingAgent(caseNo)}
      onAsk={askAgent}
    />
  );
  const metrics = (
    <DashboardMetricTiles
      metrics={data.metrics || []}
      status={sectionStatus("metrics")}
      onOpen={navigateMetric}
    />
  );
  const reminders = (
    <DashboardRejectionReminder
      items={rejections}
      total={rejectionTotal}
      loading={loading.rejections}
      status={sectionStatus("rejections")}
      onOpen={openRejection}
      onAsk={askAgent}
    />
  );
  const refreshAll = () => { retry("todos"); retry("cases"); retry("rejections"); retry("metrics"); };
  const greeting = greetingByHour(now.hour());
  const displayName = workspace.status?.identity?.display_name;
  return (
    <div className={`reference-dashboard workbench${showEmbeddedConversation ? " is-conversation" : ""}`}>
      <div className="wb-shell">
        {/* 桌面端问候语单独占一行，概况卡片只放待办和案件；手机端仍放在概况头部。 */}
        {!isNarrowViewport && (
          <header className="wb-hero">
            <DashboardGreeting greeting={greeting} name={displayName} briefing={briefing} />
            <Button className="wb-hero-refresh" onClick={refreshAll} aria-label="刷新工作台">刷新</Button>
          </header>
        )}
        {metrics}
        <div className="wb-grid">
          <div className="wb-main">
            {isNarrowViewport && <div className="wb-view-switch" aria-label="工作台视图">
              <button type="button" aria-pressed={view === "overview"} onClick={() => onViewChange("overview")}>工作概况</button>
              <button type="button" aria-pressed={view === "conversation"} onClick={() => onViewChange("conversation")}>助手对话</button>
            </div>}
            {showEmbeddedConversation ? <AssistantPanel
              workspace={workspace}
              suggestions={suggestions}
              focusRequested={assistantFocusRequested}
              onFocusHandled={onAssistantFocusHandled}
              onReturnOverview={() => onViewChange("overview")}
            /> : <DashboardOverview
              showHead={isNarrowViewport}
              greeting={greeting}
              name={displayName}
              briefing={briefing}
              todos={data.todos}
              cases={data.latest_cases}
              todoStatus={sectionStatus("todos")}
              caseStatus={sectionStatus("cases")}
              todosLoading={loading.todos}
              casesLoading={loading.cases}
              todosError={Boolean(errors.todos)}
              casesError={Boolean(errors.cases)}
              canNavigate={canNavigate}
              canOpenCase={canOpenCase}
              onNavigate={onNavigate}
              onOpenCase={(caseNo) => void openDashboardDetail("case", caseNo)}
              onRefresh={refreshAll}
            />}
          </div>
          <div className="wb-side">
            {schedule}
            {reminders}
          </div>
        </div>
      </div>
    </div>
  );
}
