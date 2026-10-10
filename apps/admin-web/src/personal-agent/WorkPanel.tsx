import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Alert, Button, Empty, Input, Segmented, Skeleton, Tag, Tooltip } from "antd";
import { AppstoreAddOutlined, ArrowRightOutlined, AuditOutlined, CheckOutlined, DownOutlined, FileTextOutlined, FileWordOutlined, FolderOpenOutlined, PaperClipOutlined, ReloadOutlined, RobotOutlined, ScheduleOutlined, SearchOutlined, TeamOutlined, UpOutlined, WalletOutlined } from "@ant-design/icons";
import { api } from "../api";
import { buildContractDetailRoute } from "../contractDetailNavigation";
import { rememberTaskDetailTarget } from "../taskDetailNavigation";
import { errorText, type WorkOverview, type WorkRecord, type WorkspaceCommand, type WorkspaceSkill, type WorkspaceStatus } from "./types";
import "./work-panel.css";

const routes: Record<string, string> = { tasks: "task-my", contracts: "contract-audit-pending", cases: "case-company", finance: "finance-payment-audit", seal: "seal-audit-pending", customers: "customer-company", investigation: "investigation-task-mine", clues: "clue-audit-pending", hr: "hr-all", documents: "documents-my", warehouse: "warehouse-list" };
const icons: Record<string, ReactNode> = { today: <ScheduleOutlined />, task: <CheckOutlined />, approval: <AuditOutlined />, case: <FolderOpenOutlined />, finance: <WalletOutlined />, seal: <FileTextOutlined />, customer: <TeamOutlined /> };
const moduleLabels: Record<string, string> = { contract: "合同", finance: "财务", seal: "用印", clue: "线索" };
const metrics = [{ command: "tasks", label: "待处理任务", route: "task-my-accepted", icon: <ScheduleOutlined />, tone: "green" }, { command: "contracts", label: "待审批合同", route: "contract-audit-pending", icon: <AuditOutlined />, tone: "amber" }, { command: "seal", label: "待审批用印", route: "seal-audit-pending", icon: <FileTextOutlined />, tone: "blue" }, { command: "clues", label: "待审批线索", route: "clue-audit-pending", icon: <SearchOutlined />, tone: "rose" }];

type Props = { status: WorkspaceStatus | null; skills: WorkspaceSkill[]; busy: boolean; refreshToken: number; decisionResult: unknown; onNavigate: (route: string) => void; onPrepare: (command: WorkspaceCommand) => void; onSkill: (skill: WorkspaceSkill) => void; onUpload: () => void; onSkills: () => void; onDraft: () => void };

export function WorkPanel({ status, skills, busy, refreshToken, decisionResult, onNavigate, onPrepare, onSkill, onUpload, onSkills, onDraft }: Props) {
  const [data, setData] = useState<WorkOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [tab, setTab] = useState("任务");
  const [keyword, setKeyword] = useState("");
  const [pendingOnly, setPendingOnly] = useState(true);
  const [expandedBusiness, setExpandedBusiness] = useState(false);
  const commands = status?.commands || [];
  const permitted = new Set(commands.map((item) => item.id));
  const availableTabs = [permitted.has("tasks") && "任务", ["contracts", "finance", "seal", "clues"].some((key) => permitted.has(key)) && "审批", permitted.has("cases") && "案件"].filter((value): value is string => !!value);
  const activeTab = availableTabs.includes(tab) ? tab : availableTabs[0];
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    void api.get<WorkOverview>("/personal-agent/workspace", { signal: controller.signal }).then(({ data: result }) => { if (!controller.signal.aborted) setData(result); }).catch((reason) => { if (!controller.signal.aborted) setError(errorText(reason, "工作清单加载失败")); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [revision, refreshToken, decisionResult]);
  const rows = useMemo(() => {
    if (!data) return [];
    const records = activeTab === "任务" ? data.my_tasks : activeTab === "审批" ? [...data.pending_contract_approvals.map((item) => ({ ...item, module: "contract" })), ...data.pending_other_approvals] : activeTab === "案件" ? data.visible_cases : [];
    return records.filter((item) => (activeTab !== "任务" || !pendingOnly || ["待接收", "待处理"].includes(item.status)) && `${item.title} ${item.serial_no} ${item.customer}`.toLowerCase().includes(keyword.trim().toLowerCase()));
  }, [data, activeTab, pendingOnly, keyword]);
  const openRecord = (item: WorkRecord) => {
    if (activeTab === "任务") { rememberTaskDetailTarget({ id: item.id, serial_no: item.serial_no, scope: "mine" }); onNavigate("task-my"); }
    else if (activeTab === "案件") onNavigate(`case-detail-${item.id}-${encodeURIComponent(item.serial_no)}`);
    else if (item.module === "contract") { const route = buildContractDetailRoute(item); if (route) onNavigate(route); }
    else if (item.module === "finance") onNavigate(routes.finance);
    else if (item.module === "seal") onNavigate(routes.seal);
    else if (item.module === "clue") onNavigate(routes.clues);
  };
  const askRecord = (item: WorkRecord) => onPrepare({ id: "record", label: item.title, icon: "today", skill_id: activeTab === "案件" ? "plain-legal-brief" : "general-office", prompt: `查询${activeTab === "任务" ? "任务" : activeTab === "案件" ? "案件" : moduleLabels[item.module || ""]}${item.serial_no}（记录ID：${item.id}）的最新情况，先列重点和需要我处理的事项，不执行写入。` });
  const today = commands.find((command) => command.id === "today");
  const businessCommands = commands.filter((command) => command.id !== "today");
  const visibleBusinessCommands = expandedBusiness ? businessCommands : businessCommands.slice(0, 6);
  const role = status?.identity.permission_role || status?.identity.staff_role || status?.identity.position || status?.identity.role;
  return <section className="law-work-panel" aria-label="律所工作台">
    <div className="law-work-heading"><div><h3>我的工作台</h3><div className="law-work-date">{new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "long" })}</div></div><Button icon={<RobotOutlined />} disabled={busy || !today} onClick={() => today && onPrepare(today)}>梳理今日工作</Button></div>
    <div className="law-work-account"><span className="law-account-avatar" aria-hidden="true"><TeamOutlined /></span><b>{status?.identity.display_name || "当前用户"}</b><span>{[status?.identity.department, role].filter(Boolean).join(" · ")}</span></div>
    {!!metrics.filter((item) => permitted.has(item.command)).length && <div className="law-work-metrics">{metrics.filter((item) => permitted.has(item.command)).map((item) => <button key={item.command} className={`law-work-metric ${item.tone}`} onClick={() => { if (item.command === "tasks") sessionStorage.setItem("sunhold:dashboard-task-tab", "pending"); onNavigate(item.route); }}><span>{item.icon}{item.label}</span><strong>{loading ? <span className="law-metric-loading" /> : error || !data ? "—" : data.todos.find((row) => row[0] === item.label)?.[1] ?? "—"}</strong><ArrowRightOutlined /></button>)}</div>}
    <section className="law-work-section"><div className="law-work-section-title"><h4>工作清单</h4><Tooltip title="刷新工作清单"><Button type="text" size="small" icon={<ReloadOutlined />} aria-label="刷新工作清单" loading={loading} onClick={() => setRevision((value) => value + 1)} /></Tooltip></div>
      {error ? <Alert type="error" showIcon title={error} action={<Button size="small" onClick={() => setRevision((value) => value + 1)}>重试</Button>} /> : loading ? <Skeleton active paragraph={{ rows: 4 }} /> : !availableTabs.length ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可访问的任务、审批或案件清单" /> : <>
        <div className="law-work-list-toolbar"><Segmented value={activeTab} options={availableTabs} onChange={(value) => setTab(String(value))} /><Input aria-label="搜索工作清单" placeholder="搜索名称、编号" prefix={<SearchOutlined />} allowClear value={keyword} onChange={(event) => setKeyword(event.target.value)} /></div>
        <div className="law-work-list-caption"><span>{activeTab === "任务" ? "最近更新的12项个人任务" : activeTab === "案件" ? "最近更新的12项可访问案件" : "与我相关的待审核事项"}</span>{activeTab === "任务" && <Segmented size="small" value={pendingOnly ? "待处理" : "全部"} options={["待处理", "全部"]} onChange={(value) => setPendingOnly(value === "待处理")} />}</div>
        {!rows.length ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={keyword ? "没有匹配的工作事项" : "当前清单暂无事项"} /> : <div className="law-work-records">{rows.map((item) => <article className={`law-work-record${item.days_remaining != null && item.days_remaining < 0 ? " overdue" : ""}`} key={`${item.module || activeTab}-${item.id}`}><div className="law-record-mark">{activeTab === "任务" ? <CheckOutlined /> : activeTab === "案件" ? <FolderOpenOutlined /> : <AuditOutlined />}</div><div className="law-record-details"><button onClick={() => openRecord(item)}>{item.title || item.serial_no}</button><div><span>{item.serial_no}</span>{item.customer && <span>{item.customer}</span>}</div>{item.deadline && <span className={item.days_remaining != null && item.days_remaining < 0 ? "law-record-overdue" : "law-record-deadline"}>截止 {item.deadline}{item.days_remaining != null && item.days_remaining < 0 ? ` · 逾期${-item.days_remaining}天` : ""}</span>}</div><div className="law-record-actions"><Tag title={item.status}>{item.status}</Tag><Tooltip title="交给智能体分析"><Button type="text" icon={<RobotOutlined />} aria-label={`分析${item.serial_no}`} disabled={busy} onClick={() => askRecord(item)} /></Tooltip><Tooltip title="打开业务页面"><Button type="text" icon={<ArrowRightOutlined />} aria-label={`打开${item.serial_no}`} onClick={() => openRecord(item)} /></Tooltip></div></article>)}</div>}
      </>}
    </section>
    <section className="law-work-section"><div className="law-work-section-title"><h4>业务入口</h4>{businessCommands.length > 6 && <Button type="text" size="small" icon={expandedBusiness ? <UpOutlined /> : <DownOutlined />} aria-expanded={expandedBusiness} onClick={() => setExpandedBusiness((value) => !value)}>{expandedBusiness ? "收起" : "全部入口"}</Button>}</div><div className="law-business-links">{visibleBusinessCommands.map((command) => <div key={command.id}><button className="law-business-open" onClick={() => onNavigate(routes[command.id])}>{icons[command.icon]}<span>{command.label}</span></button><Tooltip title="让智能体协助处理"><Button type="text" size="small" icon={<RobotOutlined />} aria-label={`智能体协助${command.label}`} disabled={busy} onClick={() => onPrepare(command)} /></Tooltip></div>)}</div></section>
    <section className="law-work-section"><div className="law-work-section-title"><h4>材料与文档</h4></div><div className="law-work-tools"><button disabled={busy} onClick={onUpload}><PaperClipOutlined /><span>上传材料</span><small>Word / PDF / 图片 / Excel</small></button><button disabled={busy} onClick={onDraft}><FileWordOutlined /><span>起草文档</span><small>办公文档与案件文书</small></button></div></section>
    <section className="law-work-section"><div className="law-work-section-title"><h4>我的技能</h4><Button type="text" size="small" icon={<AppstoreAddOutlined />} disabled={busy} onClick={onSkills}>管理技能</Button></div><div className="law-work-skills">{skills.filter((skill) => skill.available).map((skill) => <Tooltip key={skill.id} title={skill.description}><button disabled={busy} onClick={() => onSkill(skill)}><AppstoreAddOutlined />{skill.name}{skill.custom && <small>自定义</small>}</button></Tooltip>)}</div></section>
  </section>;
}
