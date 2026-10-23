import { Checkbox,Space } from "antd";
import dayjs from "dayjs";
import type { ReactNode } from "react";
import { useState } from "react";
import { getLegacyCaseDocumentGenerationItems } from "../caseDocumentGenerationActions.mjs";
import { CaseLitigantAgentDataError, normalizeCaseLitigantAgents } from "./caseLitigantAgents";
import {
CRIMINAL_CASE_TYPE,
LEGACY_CASE_PHASE_GROUPS,
LEGACY_CIVIL_PHASE_ROOTS,
LEGACY_CRIMINAL_PHASE_ROOT_ITEMS,
buildLegacyCasePhaseTree,
casePhaseChildrenForCaseType,
casePhaseRootItemsForCaseType,
isCriminalCaseType
} from "../caseOrdinarySearchParity.mjs";
import type {
CaseAgentDocument,
CaseAgentDocumentTreeNode,
CaseDetailCapabilities,
CaseFileTypeOption,
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
import type { CaseDocumentTreeItem } from "./services/legacyCaseDocumentFolders";

export { getLegacyCaseDocumentGenerationItems };
export { normalizeCaseLitigantAgents };
export { CRIMINAL_CASE_TYPE, isCriminalCaseType };

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
// 列表左侧刑事阶段面板与变更阶段弹窗共用（10.22 第 11 行）。
export const CRIMINAL_CASE_PHASE_ROOT_ITEMS = LEGACY_CRIMINAL_PHASE_ROOT_ITEMS;

// 弹窗未显式传案件类型时，接口返回了刑事专用阶段即按刑事树显示。
export const resolveCasePhasePickerCaseType = (caseType: unknown, options: CasePhaseOption[]) => {
  const explicit = String(caseType ?? "").trim();
  if (explicit) return explicit;
  return options.some((option) => isCriminalCaseType(option.case_type)) ? CRIMINAL_CASE_TYPE : "";
};

export const renderCaseLitigantAgentSummary = (value: unknown) => {
  let agents: CaseLitigantAgent[];
  try {
    agents = normalizeCaseLitigantAgents(value);
  } catch (error) {
    if (error instanceof CaseLitigantAgentDataError) return <span className="case-agent-data-error" role="alert">{error.message}</span>;
    throw error;
  }
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
  caseType,
}: {
  options: CasePhaseOption[];
  value?: number;
  onChange?: (value: number) => void;
  caseType?: string;
}) => {
  const [collapsedCodes, setCollapsedCodes] = useState<Set<string>>(() => new Set());
  const optionForPhase = (phase: string) => options.find((option) => [
    option.name,
    option.canonical_name,
  ].some((candidate) => String(candidate || "").trim() === phase));
  const pickerCaseType = resolveCasePhasePickerCaseType(caseType, options);
  const rootItems = casePhaseRootItemsForCaseType(pickerCaseType);
  const tree = (buildLegacyCasePhaseTree(
    rootItems.map((item) => ({ ...item, count: 0 })),
    options,
    {},
    casePhaseChildrenForCaseType(pickerCaseType),
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

// 移动目录可选项按案件类型区分（10.22 第 17 行）；不传案件类型时保持民事五个目录。
export const getCaseDocumentMoveCategoryOptions = (customFolders: string[] = [], caseType?: unknown) =>
  [...getCaseFormalDocumentFolders(caseType), ...customFolders]
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

export const isAiSpreadsheetGenerationRequest = (value: string) =>
  /(?:生成|制作|整理|导出|保存|转成|转换).{0,24}(?:excel|xlsx|电子表格|表格)/i.test(value)
  || /(?:excel|xlsx|电子表格|表格).{0,16}(?:文件|表格|格式)/i.test(value);

export const aiExcelDocumentName = (request: string, generatedContent = "") => {
  const explicitTitle = request.match(/标题(?:为|是)?[“"]([^”"]{1,80})[”"]/i)?.[1]?.trim();
  const generatedTitle = generatedContent.split(/\r?\n/).map((line) => line.replace(/^[#*\s|]+/, "").trim()).find(Boolean)?.slice(0, 60);
  const cleaned = request.replace(/(?:请|帮我|给我|需要|可以|能否|生成|制作|整理|导出|保存|转成|转换)/g, "")
    .replace(/(?:excel|xlsx|电子表格|表格|文件|格式)/gi, "")
    .replace(/[\\/:*?"<>|\r\n]+/g, " ").trim().slice(0, 60);
  const title = explicitTitle || (/[\p{L}\p{N}]/u.test(cleaned) ? cleaned : "") || generatedTitle || "AI生成表格";
  return `${title}-${dayjs().format("YYYYMMDD-HHmmss")}.xlsx`;
};

export const noCaseEventCapabilities: CaseEventCapabilities = { can_create: false, can_edit: false, can_delete: false };

export const AGENT_DOCUMENT_LIMIT = 12;
export const AGENT_CASE_DOCUMENT_FOLDERS = ["主体及委托资料", "起诉材料及证据", "答辩材料及证据", "法院诉讼文书", "庭审及庭后文件"];
export const AGENT_INVESTIGATION_DOCUMENT_FOLDERS = ["鉴别资料", "调查文档", "取证文档"];

// 10.22 第 17 行：旧系统刑事案件文档目录（逐字取自旧系统截图）。
// “诉讼阶段文件”沿用分组值“案件文档全部”，因此“+ 新增自定义目录”、分组筛选等原逻辑不变。
export const CRIMINAL_CASE_DOCUMENT_GROUP_LABEL = "诉讼阶段文件";
export const CRIMINAL_CASE_DOCUMENT_FOLDERS = ["委托手续及证明", "起诉书及证据", "辩论意见及证据", "法院裁判文书"];
export const CRIMINAL_AUTHORITY_DOCUMENT_FOLDERS = ["公安机关文件", "检察机关文件"];

/** “案件文档/诉讼阶段文件”分组下的固定子目录。 */
export const getCaseStageDocumentFolders = (caseType?: unknown): string[] =>
  isCriminalCaseType(caseType) ? [...CRIMINAL_CASE_DOCUMENT_FOLDERS] : [...AGENT_CASE_DOCUMENT_FOLDERS];

/** 该案件类型可上传/移动/转入的全部固定正式目录（刑事含公安机关文件、检察机关文件）。 */
export const getCaseFormalDocumentFolders = (caseType?: unknown): string[] =>
  isCriminalCaseType(caseType)
    ? [...CRIMINAL_CASE_DOCUMENT_FOLDERS, ...CRIMINAL_AUTHORITY_DOCUMENT_FOLDERS]
    : [...AGENT_CASE_DOCUMENT_FOLDERS];

/** 刑事案件不再放入民事固定目录（历史文件保留原目录显示）。 */
export const isCaseFormalDocumentFolderBlocked = (category: unknown, caseType?: unknown, customFolders: string[] = []) => {
  const name = String(category ?? "").trim();
  return isCriminalCaseType(caseType) && AGENT_CASE_DOCUMENT_FOLDERS.includes(name) && !customFolders.includes(name);
};

/** 不属于“案件文档/诉讼阶段文件”分组的目录，分组视图需排除。 */
export const getNonCaseDocumentCategories = (caseType?: unknown): string[] => [
  "AI空间", "客户文档", "合同文档", ...AGENT_INVESTIGATION_DOCUMENT_FOLDERS,
  ...(isCriminalCaseType(caseType) ? CRIMINAL_AUTHORITY_DOCUMENT_FOLDERS : []),
];

/** 上传分类选项：固定正式目录 + 按案件类型关联的文件类型 + 自定义目录 + 普通附件。 */
export const getCaseUploadCategoryOptions = ({
  caseType,
  fileTypeOptions = [],
  customFolders = [],
}: {
  caseType?: unknown;
  fileTypeOptions?: CaseFileTypeOption[];
  customFolders?: string[];
}): CaseFileTypeOption[] => {
  const fixed = getCaseFormalDocumentFolders(caseType);
  // 文件类型是树形选项（如 调查文档 › 鉴别资料），逐层去掉固定目录和刑事不再使用的民事目录。
  const keep = (options: CaseFileTypeOption[]): CaseFileTypeOption[] => options.flatMap((option) => {
    const children = option.options?.length ? keep(option.options) : undefined;
    const blocked = fixed.includes(option.value) || isCaseFormalDocumentFolderBlocked(option.value, caseType, customFolders);
    if (blocked) return children || [];
    return [children ? { ...option, options: children } : option];
  });
  const fileTypes = keep(fileTypeOptions);
  const flatten = (options: CaseFileTypeOption[]): string[] => options.flatMap((option) => [option.value, ...flatten(option.options || [])]);
  const fileTypeValues = new Set(flatten(fileTypes));
  return [
    ...fixed.map((name) => ({ value: name, label: name })),
    ...fileTypes,
    ...customFolders.filter((name) => !fixed.includes(name) && !fileTypeValues.has(name)).map((name) => ({ value: name, label: name })),
    { value: "普通附件", label: "普通附件" },
  ];
};

/**
 * 新系统案件（非 9/30 迁移旧目录）的文档目录树。民事等类型与原硬编码完全一致；
 * 刑事案件把“案件文档”换成“诉讼阶段文件”及四个子目录，并增加“公安机关文件”“检察机关文件”。
 * folderTree 是 GET /cases/{id}/document-folders 的 tree，用于带出历史分类与自定义目录。
 */
export const buildNativeCaseDocumentTree = ({
  caseType,
  folderTree = [],
  customFolders = [],
  expandedGroups = {},
}: {
  caseType?: unknown;
  folderTree?: CaseFileTypeOption[];
  customFolders?: string[];
  expandedGroups?: Record<string, boolean>;
}): CaseDocumentTreeItem[] => {
  const criminal = isCriminalCaseType(caseType);
  const caseGroup = folderTree.find((option) => option.value === "案件文档全部");
  const stageFolders = Array.from(new Set([
    ...getCaseStageDocumentFolders(caseType),
    ...(caseGroup?.options || []).map((option) => option.value).filter((name) => name && name !== "普通附件"),
    ...customFolders,
  ])).filter((name) => !criminal || !CRIMINAL_AUTHORITY_DOCUMENT_FOLDERS.includes(name));
  const items: CaseDocumentTreeItem[] = [
    { label: "案件智能体文件夹", category: "AI空间", type: "folder" },
    { label: "全部案件文档", category: "全部案件文档", type: "overview" },
    { label: "客户文档", category: "客户文档", type: "folder" },
    { label: "合同文档", category: "合同文档", type: "folder" },
    { label: "调查文档", category: "调查文档全部", type: "group" },
    { label: "鉴别资料", category: "鉴别资料", type: "child", parent: "调查文档全部" },
    { label: "调查文档", category: "调查文档", type: "child", parent: "调查文档全部" },
    { label: "取证文档", category: "取证文档", type: "child", parent: "调查文档全部" },
    { label: criminal ? CRIMINAL_CASE_DOCUMENT_GROUP_LABEL : "案件文档", category: "案件文档全部", type: "group" },
    ...stageFolders.map((label) => ({
      label, category: label, type: "child", parent: "案件文档全部",
      custom: customFolders.includes(label),
    })),
    ...(criminal ? CRIMINAL_AUTHORITY_DOCUMENT_FOLDERS.map((label) => ({ label, category: label, type: "folder" })) : []),
  ];
  return items.filter((item) => !item.parent || expandedGroups[item.parent]);
};

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

export const buildAgentDocumentTree = (documents: CaseAgentDocument[], caseType?: unknown): CaseAgentDocumentTreeNode[] => {
  const roots = ["客户文档", "合同文档", "调查文档", "案件文档"];
  return roots.map((root) => {
    const rootDocuments = documents.filter((item) => agentDocumentRootFolder(item) === root);
    // 传入刑事案件类型时，案件文档下的固定目录用刑事目录；不传保持原民事目录。
    const fixedFolders = root === "调查文档" ? AGENT_INVESTIGATION_DOCUMENT_FOLDERS : root === "案件文档" ? getCaseFormalDocumentFolders(caseType) : [];
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
  归档审核: "gold",
  待归档审核: "gold",
  亏损内审: "orange",
  亏损审核: "gold",
  亏损归档: "green",
  归档拒绝: "red",
  亏损归档拒绝: "red",
  亏损拒绝: "red",
  已归档: "green",
};

export const ARCHIVE_REVIEW_STATUSES = ["归档审核", "待归档审核", "亏损内审", "亏损审核"];
export const ARCHIVE_FINAL_STATUSES = ["已归档", "亏损归档"];
export const ARCHIVE_LOCKED_STATUSES = [...ARCHIVE_REVIEW_STATUSES, ...ARCHIVE_FINAL_STATUSES];

export const noCaseDetailWriteCapability: CaseDetailCapabilities = {
  can_write: false, can_generate_document: false, can_manage_document: false, can_upload_attachment: false, can_delete_attachment: false,
  can_create_reminder: false, can_delete_reminder: false, can_create_log: false,
  can_update_progress: false, can_change_phase: false, can_manage_hearing: false, can_create_case_task: false, can_delete_case: false, can_duplicate_case: false, can_merge_case: false, can_assign_team: false,
  can_edit_hearing_lawyer: false, can_edit_basic: false, can_edit_court_info: false, can_close_case: false, can_archive: false,
  can_edit_notary: false, can_edit_litigants: false, can_edit_settlement: false,
  can_edit_criminal_public_security: false, can_edit_criminal_procuratorate: false, can_edit_criminal_court: false,
  can_create_finance: false, can_edit_finance: false, can_delete_finance: false,
  can_refund_finance: false, can_apply_fee_payment: false, can_apply_fee_invoice: false,
  can_manage_fee_notice: false, can_confirm_fee_arrival: false, can_view_fee_receipt: false,
  can_mark_fee_unpaid: false, can_move_fee: false, can_manage_assisted_fees: false, team_role: "none",
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
