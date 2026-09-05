import { Checkbox,Space } from "antd";
import dayjs from "dayjs";
import type { ReactNode } from "react";
import { useState } from "react";
import { getLegacyCaseDocumentGenerationItems } from "../caseDocumentGenerationActions.mjs";
import {
LEGACY_CASE_PHASE_GROUPS,
LEGACY_CIVIL_PHASE_ROOTS,
buildLegacyCasePhaseTree
} from "../caseOrdinarySearchParity.mjs";
import type {
CaseAgentDocument,
CaseAgentDocumentTreeNode,
CaseDetailCapabilities,
CaseEventCapabilities,
CaseLitigantAgent,
CaseLitigantAgentField,
CaseLitigantPartyField,
CasePhaseOption,
CasePhaseTreeItem,
CaseRow,
CaseTaskPageState,
TaskRow,
} from "./types";

export { getLegacyCaseDocumentGenerationItems };

export const CASE_LITIGANT_PARTY_LABELS: Record<CaseLitigantPartyField, string> = {
  plaintiffs: "原告",
  defendants: "被告",
  third_parties: "第三人",
};

export const CASE_LITIGANT_AGENT_LABELS: Record<CaseLitigantAgentField, string> = {
  plaintiff_agents: "原告代理人",
  defendant_agents: "被告代理人",
  third_party_agents: "第三人代理人",
};

export const LEGACY_PHASE_GROUPS = new Set(LEGACY_CASE_PHASE_GROUPS);
export const CASE_PHASE_ROOT_LABELS = LEGACY_CIVIL_PHASE_ROOTS;

export const normalizeCaseLitigantAgents = (value: unknown): CaseLitigantAgent[] => Array.isArray(value)
  ? value.map((item) => {
    if (typeof item === "string") return { name: item, law_firm: "", position: "", phone: "", authority: "" };
    const agent = item && typeof item === "object" ? item as Record<string, unknown> : {};
    return {
      name: String(agent.name || "").trim(),
      law_firm: String(agent.law_firm || "").trim(),
      position: String(agent.position || "").trim(),
      phone: String(agent.phone || "").trim(),
      authority: String(agent.authority || "").trim(),
    };
  }).filter((agent) => agent.name)
  : [];

export const renderCaseLitigantAgentSummary = (value: unknown) => {
  const agents = normalizeCaseLitigantAgents(value);
  if (!agents.length) return "—";
  return <Space direction="vertical" size={2}>
    {agents.map((agent, index) => <span key={`${agent.name}-${index}`}>
      <strong>{agent.name}</strong>
      {[agent.law_firm, agent.position, agent.phone, agent.authority].filter(Boolean).join("｜") ? `（${[agent.law_firm, agent.position, agent.phone, agent.authority].filter(Boolean).join("｜")}）` : ""}
    </span>)}
  </Space>;
};

export const CasePhasePickerTree = ({
  options,
  value,
  onChange,
}: {
  options: CasePhaseOption[];
  value?: number;
  onChange?: (value: number) => void;
}) => {
  const [collapsedCodes, setCollapsedCodes] = useState<Set<string>>(() => new Set());
  const optionForPhase = (phase: string) => options.find((option) => [
    option.name,
    option.canonical_name,
  ].some((candidate) => String(candidate || "").trim() === phase));
  const tree = (buildLegacyCasePhaseTree(
    CASE_PHASE_ROOT_LABELS.map((label) => ({ label, value: label, count: 0 })),
    options,
    {},
  ) as CasePhaseTreeItem[]).map((node) => ({
    ...node,
    option: optionForPhase(node.value) || optionForPhase(node.label),
    children: node.children
      .map((child) => ({
        ...child,
        option: optionForPhase(child.value) || optionForPhase(child.label),
        children: [],
      }))
      .filter((child) => child.option),
  })).filter((node) => node.option || node.children.length);
  const renderNodes = (nodes: typeof tree, depth = 0): ReactNode => nodes.map((node) => {
    const expanded = !collapsedCodes.has(node.value);
    const selectable = Boolean(node.option) && !node.children.length && !LEGACY_PHASE_GROUPS.has(node.label);
    const selected = Number(value) === node.option?.id;
    return (
      <div key={node.value} className={`case-phase-group${node.children.length ? "" : " case-phase-group-leaf"}`}>
        <div className="case-phase-row">
          {node.children.length ? (
            <button
              aria-label={(expanded ? "收起" : "展开") + node.label}
              type="button"
              className="case-phase-toggle"
              onClick={() => setCollapsedCodes((current) => {
                const next = new Set(current);
                if (next.has(node.value)) next.delete(node.value);
                else next.add(node.value);
                return next;
              })}
            >{expanded ? "▾" : "▸"}</button>
          ) : <span className="case-phase-toggle-placeholder" />}
          {selectable ? (
            <Checkbox
              className={`case-phase-change-leaf${depth === 0 ? " case-phase-change-root-leaf" : ""}`}
              checked={selected}
              onChange={() => node.option && onChange?.(node.option.id)}
            >{node.label}</Checkbox>
          ) : (
            <span className="case-phase-change-group-label">📁 {node.label}</span>
          )}
        </div>
        {node.children.length > 0 && expanded && (
          <div className="case-phase-children">{renderNodes(node.children as typeof tree, depth + 1)}</div>
        )}
      </div>
    );
  });
  return <div className="case-phase-tree case-phase-change-tree">{renderNodes(tree)}</div>;
};

export const caseDocumentTypes = [
  ["identification_letter", "鉴定函"],
  ["authorization-letter", "授权委托书"], ["archive-letter", "归档函"], ["gd-authorization-letter", "广东版授权委托书"], ["compensation-letter", "赔偿函"],
  ["law-firm-letter", "律师事务所函"], ["identity-certificate", "主体身份证明"], ["settlement-list", "结算提成表"],
  ["first-instance-appellant-lawyer-letter", "一审上诉人律师函"], ["first-instance-appellee-lawyer-letter", "一审被上诉人律师函"],
  ["second-instance-appellant-lawyer-letter", "二审上诉人律师函"], ["second-instance-appellee-lawyer-letter", "二审被上诉人律师函"], ["execution-lawyer-letter", "执行律师函"],
  ["gd-first-instance-appellant-lawyer-letter", "广东版一审上诉人律师函"], ["gd-first-instance-appellee-lawyer-letter", "广东版一审被上诉人律师函"],
  ["gd-second-instance-appellant-lawyer-letter", "广东版二审上诉人律师函"], ["gd-second-instance-appellee-lawyer-letter", "广东版二审被上诉人律师函"], ["gd-execution-lawyer-letter", "广东版执行律师函"],
] as const;

export const getCaseDocumentMoveCategoryOptions = (customFolders: string[] = []) =>
  ["主体及委托资料", "起诉材料及证据", "答辩材料及证据", "法院诉讼文书", "庭审及庭后文件", ...customFolders]
    .filter((value, index, values) => value && values.indexOf(value) === index)
    .map((value) => ({ value, label: value }));

export const CASE_TASK_DEFAULT_PAGE = 1;
export const CASE_TASK_DEFAULT_PAGE_SIZE = 15;

export const caseTaskTypeLabel = (row: TaskRow) => {
  if (row.creation_mode === "自动" || row.creation_mode === "人工") return row.creation_mode;
  const taskType = String(row.task_type || "").trim();
  if (taskType === "固定任务" || taskType === "自动任务" || row.source === "自动任务" || row.source === "自动") return "自动";
  return "人工";
};

export const normalizeCaseTaskPageState = (
  payload: any,
  fallbackPage = CASE_TASK_DEFAULT_PAGE,
  fallbackPageSize = CASE_TASK_DEFAULT_PAGE_SIZE,
): CaseTaskPageState => {
  const items = Array.isArray(payload?.items) ? payload.items : [];
  const total = Number.isFinite(Number(payload?.total)) ? Number(payload.total) : items.length;
  const pageSize = Number.isFinite(Number(payload?.page_size)) && Number(payload.page_size) > 0
    ? Number(payload.page_size)
    : fallbackPageSize;
  const page = Number.isFinite(Number(payload?.page)) && Number(payload.page) > 0
    ? Number(payload.page)
    : fallbackPage;
  const pages = Number.isFinite(Number(payload?.pages)) && Number(payload.pages) >= 0
    ? Number(payload.pages)
    : total
      ? Math.ceil(total / pageSize)
      : 0;
  return { items, total, page, pageSize, pages };
};

export const isAiWordGenerationRequest = (value: string) =>
  /(?:生成|起草|新建|制作|编写|撰写|整理).{0,24}(?:word|docx|文档|起诉状|答辩状|代理词|法律意见书|律师函|申请书|合同|函件)/i.test(value)
  || /(?:我要(?:的)?(?:是)?|我需要|给我|改成|保存为|转成|导出为).{0,16}(?:word|docx|文档|文书|材料|文件)/i.test(value);

export const isExistingAnswerWordConversionRequest = (value: string) =>
  /(?:我要(?:的)?(?:是)?|改成|保存为|转成|导出为).{0,16}(?:word|docx|文档|文书|材料|文件)/i.test(value);

export const isUsableAiDocumentContent = (value: string) => {
  const content = String(value || "").trim();
  return content.length >= 80 && !/模型本轮生成失败|正在分析案件空间/.test(content);
};

export const aiWordDocumentName = (request: string, generatedContent = "") => {
  const explicitTitle = request.match(/标题(?:为|是)?[“\"]([^”\"]{1,80})[”\"]/i)?.[1]?.trim();
  const generatedTitle = generatedContent.split(/\r?\n/).map((line) => line.replace(/^[#*\s]+/, "").trim()).find(Boolean)?.slice(0, 60);
  const cleaned = request
    .replace(/(?:请|帮我|给我|需要|可以|能否)/g, "")
    .replace(/(?:我要(?:的)?(?:是)?|不是这个|改成|保存为|转成|导出为)/g, "")
    .replace(/(?:生成|起草|新建|制作|编写|撰写|整理)/g, "")
    .replace(/(?:word|docx|格式|文档)/gi, "")
    .replace(/[\\/:*?"<>|\r\n]+/g, " ")
    .trim()
    .slice(0, 60);
  const meaningfulRequestTitle = /[\p{L}\p{N}]/u.test(cleaned) ? cleaned : "";
  const title = explicitTitle || (isExistingAnswerWordConversionRequest(request) ? generatedTitle : meaningfulRequestTitle) || generatedTitle || "AI生成文书";
  return `${title}-${dayjs().format("YYYYMMDD-HHmmss")}.docx`;
};

export const noCaseEventCapabilities: CaseEventCapabilities = { can_create: false, can_edit: false, can_delete: false };

export const AGENT_DOCUMENT_LIMIT = 12;
export const AGENT_CASE_DOCUMENT_FOLDERS = ["主体及委托资料", "起诉材料及证据", "答辩材料及证据", "法院诉讼文书", "庭审及庭后文件"];
export const AGENT_INVESTIGATION_DOCUMENT_FOLDERS = ["鉴别资料", "调查文档", "取证文档"];

export const agentDocumentCategoryFolder = (item: CaseAgentDocument): string => String(item.category || "未分类").trim() === "调查资料" ? "调查文档" : String(item.category || "未分类").trim() || "未分类";

export const agentDocumentRootFolder = (item: CaseAgentDocument): string => {
  if (item.source_module === "customer") return "客户文档";
  if (item.source_module === "contract") return "合同文档";
  const category = agentDocumentCategoryFolder(item);
  if (AGENT_INVESTIGATION_DOCUMENT_FOLDERS.includes(category)) return "调查文档";
  if (AGENT_CASE_DOCUMENT_FOLDERS.includes(category)) return "案件文档";
  if (["clue", "investigation"].includes(String(item.source_module || ""))) return "调查文档";
  return "案件文档";
};

export const buildAgentDocumentTree = (documents: CaseAgentDocument[]): CaseAgentDocumentTreeNode[] => {
  const roots = ["客户文档", "合同文档", "调查文档", "案件文档"];
  return roots.map((root) => {
    const rootDocuments = documents.filter((item) => agentDocumentRootFolder(item) === root);
    const fixedFolders = root === "调查文档" ? AGENT_INVESTIGATION_DOCUMENT_FOLDERS : root === "案件文档" ? AGENT_CASE_DOCUMENT_FOLDERS : [];
    if (!fixedFolders.length) {
      return { key: `folder:${root}`, title: root, selectable: false, disabled: !rootDocuments.length, children: rootDocuments.map((item) => ({ key: `document:${item.id}`, title: item.original_name, selectable: false })) };
    }
    const dynamicFolders = rootDocuments.map(agentDocumentCategoryFolder).filter((name) => !fixedFolders.includes(name));
    return {
      key: `folder:${root}`,
      title: root,
      selectable: false,
      disabled: !rootDocuments.length,
      children: Array.from(new Set([...fixedFolders, ...dynamicFolders])).map((folder) => {
        const items = rootDocuments.filter((item) => agentDocumentCategoryFolder(item) === folder);
        return { key: `folder:${root}:${folder}`, title: folder, selectable: false, disabled: !items.length, children: items.map((item) => ({ key: `document:${item.id}`, title: item.original_name, selectable: false })) };
      }),
    };
  });
};

export const getCustomCaseDocumentFolders = (row?: CaseRow | null): string[] => {
  const values = row?.data?.custom_case_document_folders;
  return Array.isArray(values) ? Array.from(new Set(values.map((value: unknown) => String(value || "").trim()).filter(Boolean))) : [];
};

export const caseDetailDate = (value: unknown): string => String(value || "").slice(0, 10) || "—";

export const caseDetailNames = (value: unknown): string => {
  if (Array.isArray(value)) return value.map((item) => String(item || "").trim()).filter(Boolean).join("、") || "—";
  return String(value || "").trim() || "—";
};

export const DEFAULT_CASE_ATTACHMENT_CATEGORY = "普通附件";

export const caseStatuses = [
  "等待公证书",
  "等待审核公证书",
  "待立案审批",
  "新案待分配",
  "文书准备",
  "一审立案受理",
  "一审准备开庭",
  "待上诉",
  "二审",
  "执行",
];

export const statusColors: Record<string, string> = {
  进行中: "blue",
  等待公证书: "gold",
  等待审核公证书: "purple",
  待立案审批: "gold",
  新案待分配: "orange",
  文书准备: "blue",
  一审立案受理: "cyan",
  一审准备开庭: "purple",
  待上诉: "red",
  二审: "geekblue",
  执行: "volcano",
  待归档审核: "gold",
  亏损内审: "orange",
  亏损审核: "gold",
  亏损归档: "green",
  亏损归档拒绝: "red",
  已归档: "green",
};

export const ARCHIVE_REVIEW_STATUSES = ["待归档审核", "亏损内审", "亏损审核"];
export const ARCHIVE_FINAL_STATUSES = ["已归档", "亏损归档"];
export const ARCHIVE_LOCKED_STATUSES = [...ARCHIVE_REVIEW_STATUSES, ...ARCHIVE_FINAL_STATUSES];

export const noCaseDetailWriteCapability: CaseDetailCapabilities = {
  can_write: false, can_generate_document: false, can_upload_attachment: false, can_delete_attachment: false,
  can_create_reminder: false, can_delete_reminder: false, can_create_log: false,
  can_update_progress: false, can_change_phase: false, can_manage_hearing: false, can_create_case_task: false, can_delete_case: false, can_duplicate_case: false, can_merge_case: false, can_assign_team: false,
  can_edit_hearing_lawyer: false, can_edit_basic: false, can_edit_court_info: false, can_close_case: false, can_archive: false,
  can_create_finance: false, can_manage_assisted_fees: false, team_role: "none",
  reason: "当前账号没有案件详情办理权限",
};

// Module-level utility functions (originally exported from CaseCenterPage.tsx)
export const scopeCasesByListRoute = (rows: CaseRow[], initialView: string) => {
  const routeCaseType = initialView.includes("civil") ? "民事案件"
    : initialView.includes("criminal") ? "刑事案件"
      : initialView.includes("administrative") ? "行政案件及国家赔偿"
        : initialView.includes("counsel") ? "法律顾问"
          : initialView.includes("arbitration") ? "仲裁" : "";
  return rows.filter((row) => !routeCaseType || (row.data.case_type || "民事案件") === routeCaseType);
};

export const buildCasePhaseItems = (rows: CaseRow[], initialView: string, items: {label:string;value:string}[]) => {
  const routeCases = scopeCasesByListRoute(rows, initialView);
  return items.map((item) => ({...item, count: routeCases.filter((row) => row.status === item.value).length}));
};

export const buildCasePhaseItemsFromCounts = (counts: Record<string, number>, items: {label:string;value:string}[]) =>
  items.map((item) => ({...item, count: Number(counts[item.value] || 0)}));

export const getCasePhaseDefinitions = (initialView: string, defaultItems: {label:string;value:string}[], criminalItems: {label:string;value:string}[]) => {
  if (initialView === "case-company-arbitration") return [
    {label:"待分配",value:"新案待分配"},
    {label:"文书准备",value:"文书准备"},
    {label:"仲裁阶段",value:"仲裁阶段"},
    {label:"申诉阶段",value:"申诉阶段"},
    {label:"执行立案",value:"执行立案"},
    {label:"归档阶段",value:"归档阶段"},
  ];
  if (initialView.includes("counsel")) return [
    {label:"待分配",value:"新案待分配"},
    {label:"服务中",value:"服务中"},
    {label:"续费中",value:"续费中"},
    {label:"已过期",value:"已过期"},
    {label:"归档阶段",value:"归档阶段"},
  ];
  return initialView.includes("criminal") ? criminalItems : defaultItems;
};

export const getCompanyCriminalQueryFields = () => [
  ["prosecutor", "公诉机关", "公诉机关"],
  ["serial_no", "案号", "案号"],
  ["keyword", "关键字", "案号、法院号、案件名称、客户名称"],
  ["defendant", "被告", "被告"],
  ["notary_no", "公证书号", "公证书号"],
  ["status", "案件阶段", "案件阶段"],
  ["hearing_lawyer", "开庭律师", "开庭律师"],
  ["handling_lawyer", "经办律师", "经办律师"],
  ["court", "法院名称", "法院名称"],
];

export const getCompanyArbitrationQueryFields = () => [
  ["plaintiff", "申请人", "申请人"],
  ["serial_no", "案号", "案号"],
  ["keyword", "关键字", "案号、法院号、案件名称、客户名称"],
  ["defendant", "被申请人", "被申请人"],
  ["notary_no", "公证书号", "公证书号"],
  ["status", "案件阶段", "案件阶段"],
  ["hearing_lawyer", "开庭律师", "开庭律师"],
  ["handling_lawyer", "经办律师", "经办律师"],
  ["court", "仲裁机构", "仲裁机构"],
];

export const getLegacyGroupedCaseColumnSchema = () => [
  { key: "base", title: "基本信息", width: "12%" },
  { key: "parties", title: "当事人信息", width: "17%" },
  { key: "court", title: "法院信息", width: "19%" },
  { key: "lawyer", title: "委托律师", width: "13%" },
  { key: "phase", title: "阶段信息", width: "13%" },
  { key: "task", title: "任务信息", width: "20%" },
];

export const getCompanyScheduleQueryFields = (): [string,string,string?,string?][] => [
  ["plaintiff", "原告/申请人/公诉机关", "text", "原告"],
  ["serial_no", "案号", "text", "案号"],
  ["handling_lawyer", "经办律师", "text", "经办律师"],
  ["keyword", "关键字", "text", "案号、法院号、案件名称、客户名称"],
  ["defendant", "被告/被申请人", "text", "被告"],
  ["notary_no", "公证书号", "text", "公证书号"],
  ["hearing_lawyer", "开庭律师", "text", "开庭律师"],
  ["court", "法院/机构", "text", "法院名称"],
  ["third_party", "第三人/受害人", "text", "第三人"],
  ["investigator", "调查员", "text", "调查员"],
  ["assistant", "律师助理", "text", "律师助理"],
  ["document_name", "文档名称", "text", "文档名称"],
  ["source_range", "案源时间", "date", ""],
  ["hearing_range", "开庭时间", "date", ""],
  ["case_type", "案件类型", "select", "请选择"],
  ["log_content", "日志内容", "text", "日志内容"],
];

export const getCompanyScheduleQueryInitialValues = (today: unknown) => ({ hearing_range: [today, null] });

export const getCompanyCriminalColumnSchema = () => [
  {key:"serial_no",title:"案件编号",width:150},
  {key:"charge",title:"罪名",width:180},
  {key:"prosecutor",title:"公诉机关",width:180},
  {key:"defendant",title:"被告人/犯罪嫌疑人",width:190},
  {key:"status",title:"案件阶段",width:120},
  {key:"court",title:"法院名称",width:180},
  {key:"hearing_at",title:"开庭时间",width:120},
  {key:"handling_lawyer",title:"经办律师",width:140},
  {key:"assistant",title:"律师助理",width:110},
  {key:"source_person",title:"案源人",width:110},
  {key:"remaining_days",title:"剩余时间",width:90},
  {key:"spacer",title:"",width:40},
];

export const getCompanyArbitrationColumnSchema = () => [
  {key:"serial_no",title:"案件编号",width:150},
  {key:"charge",title:"案由",width:180},
  {key:"plaintiff",title:"申请人",width:180},
  {key:"defendant",title:"被申请人",width:190},
  {key:"status",title:"案件阶段",width:120},
  {key:"court",title:"仲裁机构",width:180},
  {key:"hearing_at",title:"开庭时间",width:120},
  {key:"handling_lawyer",title:"经办律师",width:140},
  {key:"assistant",title:"律师助理",width:110},
  {key:"source_person",title:"案源人",width:110},
  {key:"remaining_days",title:"剩余时间",width:90},
  {key:"spacer",title:"",width:40},
];

export const shouldUseCompanyCriminalQueryFields = (initialView: string) => initialView === "case-company-criminal";
export const shouldUseCompanyArbitrationQueryFields = (initialView: string) => initialView === "case-company-arbitration";
export const shouldUseCompanyArbitrationColumns = (initialView: string) => initialView === "case-company-arbitration";
export const shouldUseCompanyScheduleQueryFields = (initialView: string) => initialView === "case-company-schedule";
export const shouldShowCompanyScheduleActions = (initialView: string, rowCount: number) => initialView !== "case-company-schedule" || rowCount > 0;
export const shouldUseCompanySchedulePagination = (initialView: string) => initialView === "case-company-schedule";
export const getCompanySchedulePageSizeOptions = () => ["10", "15", "20", "50", "100", "200"];
export const shouldShowCompanyScheduleSinglePageJumper = (initialView: string, rowCount: number, pageSize: number) => initialView === "case-company-schedule" && rowCount > 0 && rowCount <= pageSize;

export const isCivilCaseType = (caseType: unknown) => ["民事案件", "民事争议", "民事"].includes(String(caseType || "").trim());
export const isNormalCaseBasicType = (caseType: unknown) => isCivilCaseType(caseType) || ["刑事案件", "行政案件及国家赔偿"].includes(String(caseType || "").trim());

export const getLegacyCaseDetailPrimaryOperationLabels = () => [
  "修改基本信息",
  "修改案件阶段",
  "修改公证信息",
  "修改开庭律师",
  "修改当事人",
  "修改法院信息",
  "修改诉讼或判决金额",
  "申请归档",
  "更多操作",
];

export const getLegacyCaseDetailMoreOperationLabels = () => [
  "生成授权委托书",
  "生成一审所函(我方原告)",
  "生成一审所函(我方被告)",
  "生成二审所函(我方上诉)",
  "生成二审所函(对方上诉)",
  "生成执行所函",
  "生成身份证明",
  "案件合并",
  "复制案件",
];

export const getCompanyScheduleCourtLevels = () => [
  ["first", "一审"],
  ["second", "二审"],
  ["execution", "执行"],
  ["retrial", "再审"],
] as const;

export const isMyCaseListRoute = (initialView: string) =>
  initialView === "case-mine" || initialView.startsWith("case-mine-");

export const isCompanyCaseListRoute = (initialView: string) =>
  initialView === "case-company" || initialView.startsWith("case-company-");

export const shouldShowCaseListActions = (initialView: string) =>
  isMyCaseListRoute(initialView) || isCompanyCaseListRoute(initialView);
