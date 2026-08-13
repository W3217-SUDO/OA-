export type CaseCreateMode = "normal" | "counsel";
export type CaseEditKind = "normal" | "arbitration";

export const CASE_CREATE_REQUIRED_FIELDS = {
  normal: ["customer", "contract_record_id", "client_position", "cause_or_charge", "title", "handling_lawyers"],
  counsel: ["customer", "contract_record_id", "counsel_type", "counsel_range", "title", "handling_lawyers"],
} as const;

export const CASE_MUTATION_BLOCKED_STATUSES = ["待归档审核", "已归档", "已合并"] as const;
export const CASE_EXECUTION_STATUSES = [
  "一审待执行", "二审待执行", "准备材料", "提交法院", "执行受理",
  "执行中止", "执行结案", "执行终本", "执行终结",
  // Preserve the local values that were already exposed by the Case page.
  "未开始", "执行中", "已执行",
] as const;
export const CASE_CLUE_CONVERSION_ENDPOINT = "/investigations/clues/batch-cases";

const text = (value: unknown) => String(value ?? "").trim();
const list = (value: unknown) => Array.isArray(value) ? value.map(text).filter(Boolean) : [];
const idList = (value: unknown) => Array.from(new Set(
  (Array.isArray(value) ? value : []).map((item) => Number(item)).filter((item) => Number.isInteger(item) && item > 0),
));
const dateText = (value: unknown) => {
  if (value && typeof value === "object" && "format" in value && typeof value.format === "function") {
    return value.format("YYYY-MM-DD");
  }
  return text(value);
};

export const getCaseCreateValidationError = (draft: Record<string, unknown>, mode: CaseCreateMode) => {
  if (!text(draft.customer)) return "请选择客户.";
  if (!Number(draft.contract_record_id)) return "请选择合同.";
  if (mode === "counsel" && !text(draft.counsel_type)) return "请输入顾问类型.";
  if (mode === "counsel" && (!Array.isArray(draft.counsel_range) || !draft.counsel_range[0] || !draft.counsel_range[1])) return "请选择顾问期限.";
  if (mode !== "counsel" && !text(draft.client_position)) return "请选择客户诉讼地位.";
  if (mode !== "counsel" && !text(draft.cause_or_charge)) return "请输入案由或罪名.";
  if (!text(draft.title)) return "请输入案件名称.";
  if (!list(draft.handling_lawyers).length) return "请按顺序录入经办律师.";
  return "";
};

export const buildCaseCreatePayload = (
  draft: Record<string, unknown>,
  context: { mode: CaseCreateMode; routeType: string; owner?: string; counselStart?: unknown; counselEnd?: unknown },
) => ({
  contract_record_id: Number(draft.contract_record_id),
  title: text(draft.title),
  status: text(draft.status) || "新案待分配",
  owner: text(draft.owner) || text(context.owner) || "admin",
  case_type: text(draft.case_type) || context.routeType,
  client_position: context.mode === "counsel" ? "" : text(draft.client_position),
  cause_or_charge: context.mode === "counsel" ? "" : text(draft.cause_or_charge),
  right_type: context.mode === "counsel" ? "" : text(draft.right_type),
  opponent: text(draft.opponent) || list(draft.defendants).join("、"),
  source_person: text(draft.source_person),
  counsel_type: context.mode === "counsel" ? text(draft.counsel_type) : "",
  counsel_start: context.mode === "counsel" ? dateText(context.counselStart ?? (Array.isArray(draft.counsel_range) ? draft.counsel_range[0] : "")) : null,
  counsel_end: context.mode === "counsel" ? dateText(context.counselEnd ?? (Array.isArray(draft.counsel_range) ? draft.counsel_range[1] : "")) : null,
  handling_lawyers: list(draft.handling_lawyers),
  assistant: text(draft.assistant),
  investigator: text(draft.investigator),
  investigation_clue: text(draft.investigation_clue),
});

export const getCaseEditValidationError = (draft: Record<string, unknown>) => {
  if (!Number(draft.customer_record_id)) return "请选择可见且有效的客户.";
  if (!text(draft.case_phase)) return "请选择案件阶段.";
  if (!text(draft.cause_or_charge)) return "请输入案由或罪名.";
  if (!text(draft.title)) return "请输入案件名称.";
  if (!list(draft.handling_lawyers).length) return "请选择有效的经办律师.";
  return "";
};

export const normalizeCaseEditPayload = (draft: Record<string, unknown>, kind: CaseEditKind) => ({
  customer_record_id: Number(draft.customer_record_id),
  title: text(draft.title),
  case_phase: text(draft.case_phase),
  cause_or_charge: text(draft.cause_or_charge),
  handling_lawyers: list(draft.handling_lawyers),
  assistant: text(draft.assistant),
  investigator: text(draft.investigator),
  investigation_clue_ids: idList(draft.investigation_clue_ids),
  ...(kind === "normal" ? { business_owner: text(draft.business_owner), right_type: text(draft.right_type) } : {}),
  comment: text(draft.comment),
});

export const getClueConversionIssues = ({
  clueIds,
  contractRecordId,
  clues,
}: {
  clueIds: unknown;
  contractRecordId: unknown;
  clues: Array<{ id?: unknown; serial_no?: unknown; status?: unknown; data?: Record<string, unknown> }>;
}) => {
  const ids = idList(clueIds);
  const issues: string[] = [];
  if (!ids.length) issues.push("请选择至少一条调查线索");
  if (!Number(contractRecordId)) issues.push("请选择合同");
  const byId = new Map(clues.map((clue) => [Number(clue.id), clue]));
  for (const id of ids) {
    const clue = byId.get(id);
    if (!clue) {
      issues.push(`线索 ${id} 不存在`);
    } else if (clue.status === "已转案件" || Number(clue.data?.converted_case_id) > 0) {
      issues.push(`${text(clue.serial_no) || id} 已经转为案件`);
    }
  }
  return issues;
};

export const buildClueConversionPayload = ({
  clueIds,
  contractRecordId,
  caseType,
  court,
}: {
  clueIds: unknown;
  contractRecordId: unknown;
  caseType?: unknown;
  court?: unknown;
}) => ({
  clue_ids: idList(clueIds),
  contract_record_id: Number(contractRecordId),
  case_type: text(caseType) || "民事案件",
  court: text(court),
});

export const getCaseMutationBlockReason = (status: unknown) => CASE_MUTATION_BLOCKED_STATUSES.includes(text(status) as typeof CASE_MUTATION_BLOCKED_STATUSES[number])
  ? "归档中、已归档或已合并案件不能参与此操作"
  : "";

export const buildCaseDuplicateRequest = (row: { id: unknown; serial_no?: unknown }) => ({
  path: `/cases/${Number(row.id)}/duplicate`,
  source_case_no: text(row.serial_no),
});

export const buildCaseMergePayload = (values: { source_case_no?: unknown; comment?: unknown }) => ({
  source_case_no: text(values.source_case_no),
  comment: text(values.comment),
});

export const buildCaseExecutionStatusPayload = (caseNos: unknown, executionStatus: unknown, comment: unknown = "") => ({
  case_nos: list(caseNos).join(","),
  execution_status: text(executionStatus),
  comment: text(comment),
});

export const buildCasePhaseChangePayload = (caseNos: unknown, phaseId: unknown, phaseName: unknown, comment: unknown = "") => ({
  case_nos: list(caseNos).join(","),
  case_phase_id: Number(phaseId) || null,
  case_phase_name: text(phaseName),
  comment: text(comment),
});

export const buildCaseProgressPayload = (values: Record<string, unknown>) => ({
  first_instance_court: text(values.first_instance_court),
  first_instance_case_no: text(values.first_instance_case_no),
  courtroom: text(values.courtroom),
  judge: text(values.judge),
  clerk: text(values.clerk),
  judgment_date: values.judgment_date ? dateText(values.judgment_date) : null,
  judgment_document_no: text(values.judgment_document_no),
  second_instance_court: text(values.second_instance_court),
  second_instance_case_no: text(values.second_instance_case_no),
  comment: text(values.comment),
});

export const buildCasePaymentContext = ({
  caseRecordId,
  caseNo,
  feeId,
  feeNo,
}: {
  caseRecordId?: unknown;
  caseNo?: unknown;
  feeId?: unknown;
  feeNo?: unknown;
}) => ({
  case_record_id: Number(caseRecordId) || undefined,
  case_no: text(caseNo),
  fee_id: Number(feeId) || undefined,
  fee_no: text(feeNo),
});
