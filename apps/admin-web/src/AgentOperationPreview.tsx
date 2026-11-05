import { Alert, Descriptions, Radio, Space, Tag } from "antd";
import { useState } from "react";
import { isAxiosError } from "axios";
import "./agent-center.css";

export type AgentActionPreview = {
  target?: string;
  changes?: { field: string; before?: unknown; before_read?: boolean; after: unknown }[];
  create?: Record<string, unknown>;
  operation_name?: string;
  tool_name?: string;
  method?: string;
  path?: string;
  path_template?: string;
  params?: Record<string, unknown>;
  original_values?: string;
  requires_confirmation?: boolean;
  /** 501137：后端随预览给出的参数中文名和代码值中文。 */
  field_labels?: Record<string, string>;
  value_labels?: Record<string, Record<string, string>>;
  /** 陶国南 11-05 09:14：卡片上要用户选的一项（如两份以上合同时选费用归属合同），选了才能确认。 */
  choice?: { field: string; label?: string; options: { value: string | number; label: string }[] };
  /** 501634（tgn 11-05 07:22）：这次动了案件详情哪几块（诉讼标的、案件基本信息、法院信息、当事人、经办律师信息等）。 */
  sections?: string[];
};

export type AgentApprovalAction = {
  id: string;
  type: string;
  summary: string;
  payload?: Record<string, unknown>;
  preview?: AgentActionPreview;
};

const ACTION_TYPE_NAMES: Record<string, string> = {
  "case.update": "修改案件字段", "case.data.update": "修改案件信息",
  "case.task.create": "新建案件任务", "case.reminder.create": "新建期限提醒",
  "customer.update": "修改客户资料", "contract.update": "修改合同资料",
  "case.delete": "删除案件", "customer.delete": "删除客户", "contract.delete": "删除合同",
  create_task: "新建任务", approve_contract: "合同审批",
};
const ACTION_FIELD_NAMES: Record<string, string> = {
  title: "名称", customer: "客户", status: "状态", description: "说明",
  court: "法院", first_instance_court: "一审法院", first_instance_case_no: "一审案号",
  second_instance_court: "二审法院", second_instance_case_no: "二审案号",
  cause_or_charge: "案由", case_stage: "案件阶段", filing_date: "立案日期",
  acceptance_date: "受理日期", judgment_date: "判决日期", effective_date: "生效日期",
  archive_no: "档案号", paper_archive_location: "纸质档案位置", client_position: "客户诉讼地位",
  owner: "负责人", deadline: "截止日期", reminder_date: "提醒日期", priority: "优先级", content: "正文",
  name: "文件名", handling_lawyers: "经办律师", handling_lawyer_usernames: "经办律师账号",
  case_id: "案件", id: "案件", hearing_lawyer: "开庭律师", hearing_lawyers: "开庭律师",
  handling_lawyer: "经办律师", customer_manager: "客户负责人", assistant: "助理", comment: "备注",
  module: "业务类型", serial_no: "案号", record_id: "业务记录", target_id: "目标记录",
  // 501137：老确认记录没有后端显示名时的常用参数中文名。
  task_id: "任务ID", task_ids: "任务ID", action: "动作", recipient: "接收人账号", end_at: "结束时间", start_at: "开始时间",
  remark: "备注", reason: "原因", amount: "金额", fee_type: "费用类型", fee_id: "费用ID", fee_ids: "费用ID",
  contract_id: "合同ID", contract_no: "合同编号", case_no: "案号", level: "审级", court_case_no: "法院案号",
  hearing_date: "开庭日期", hearing_time: "开庭时间", judge: "法官", clerk: "书记员", approved: "审批结论",
  finance_scope: "财务中心", payment_id: "到账ID", invoice_no: "发票号", collaborators: "协作人",
};
const PARAMETER_GROUP_NAMES: Record<string, string> = {
  path: "相关信息", query: "相关信息", body: "确认信息", files: "附件信息",
  // 业务工具整体确认时列出的办理步骤（陶威 11-01：所有写操作先确认）。
  steps: "办理步骤",
};
const USER_FACING_FIELD_NAMES: Record<string, string> = {
  case_id: "案件",
  hearing_lawyer: "开庭律师",
  hearing_lawyers: "开庭律师",
  handling_lawyer: "经办律师",
  handling_lawyers: "经办律师",
  customer_manager: "客户负责人",
  assistant: "助理",
  comment: "备注",
};
// 这些字段只用于前后端校验，不属于用户需要确认的业务信息。
const HIDDEN_PARAMETER_FIELDS = new Set([
  "conversation_id", "message_index", "expected_content_sha256", "request_id",
]);
// 501137：前端兜底的代码值中文（老确认记录没有 value_labels 时用）。
const DEFAULT_VALUE_NAMES: Record<string, Record<string, string>> = {
  action: { accept: "接受任务", reject: "拒绝任务", handoff: "转交任务", complete: "完成任务", confirm: "发起人确认完成",
    restart: "重启任务", feedback: "任务沟通留言", withdraw: "撤回", rollback: "回滚", resend: "重新发送", start: "开始处理", assign: "指派" },
  finance_scope: { firm: "财务中心（律所）", platform: "平台财务中心", internal: "内部" },
  level: { first: "一审", second: "二审", retrial: "再审" },
};
// 结果里常见的键（执行结果、办理步骤）。
const RESULT_FIELD_NAMES: Record<string, string> = {
  mode: "办理方式", steps: "办理步骤", step: "步骤", purpose: "内容", kind: "读写", status: "状态", result: "结果",
  error: "错误", failed_step: "失败步骤", problem: "问题", notes: "说明", id: "ID", serial_no: "编号", title: "名称",
  request_id: "确认单号", summary: "摘要", message: "说明", detail: "说明", items: "明细", total: "合计", created: "新建",
  updated: "更新", deleted: "删除", count: "数量", name: "名称", task: "任务", tasks: "任务", case: "案件", contract: "合同",
  customer: "客户", fee: "费用", invoice: "发票", payment: "付款", deadline: "截止日期", amount: "金额", next_step: "下一步",
  confirmation_url: "确认页面", isError: "是否出错",
};
// 只供系统用、不给用户看的键。
const HIDDEN_RESULT_FIELDS = new Set(["tool", "arguments", "uri", "download_url", "mime_type", "type", "artifact_id", "resource_id", "structuredContent", "content"]);
const hasChinese = (text: string) => /[\u4e00-\u9fff]/.test(text);
const fieldName = (field: string, preview?: AgentActionPreview) => preview?.field_labels?.[field] || ACTION_FIELD_NAMES[field]
  || RESULT_FIELD_NAMES[field] || (hasChinese(field) ? field : "其他信息");
const codeValue = (field: string, value: unknown, preview?: AgentActionPreview): unknown => {
  // 501634：编号按预览时查到的案号、名称显示。
  if (typeof value === "number") return preview?.value_labels?.[field]?.[String(value)] ?? value;
  if (typeof value !== "string") return value;
  const known = preview?.value_labels?.[field]?.[value] ?? DEFAULT_VALUE_NAMES[field]?.[value];
  if (known !== undefined) return known;
  // 501634：老卡片没有人员姓名时，系统账号至少显示“系统”，不露英文。
  if (/^(system|feedback-bot)$/i.test(value) && /(owner|lawyers?|investigators?|assistants?|person|handler|recipients?|collaborators|participants|approvers?|manager|initiator|officer|_username)$/.test(field)) return "系统";
  return value;
};
/** 把对象逐行写成“中文名：值”，不显示代码格式和英文键名。 */
export const readableValue = (value: unknown, preview?: AgentActionPreview, field = "", depth = 0): string => {
  value = codeValue(field, value, preview);
  if (value === undefined) return "未读取";
  if (value === null) return "空值";
  if (value === "") return "空字符串";
  if (typeof value === "boolean") return value ? "是" : "否";
  const indent = "  ".repeat(depth);
  if (Array.isArray(value)) {
    if (!value.length) return "无";
    if (value.every((item) => item === null || typeof item !== "object")) return value.map((item) => readableValue(item, preview, field, depth)).join("、");
    return value.map((item, index) => `${indent}第${index + 1}项：\n${readableValue(item, preview, field, depth + 1)}`).join("\n");
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).filter(([key]) => !HIDDEN_RESULT_FIELDS.has(key) && !HIDDEN_PARAMETER_FIELDS.has(key));
    if (!entries.length) return "无";
    return entries.map(([key, item]) => {
      const text = readableValue(item, preview, key, depth + 1);
      return item !== null && typeof item === "object" && text.includes("\n") ? `${indent}${fieldName(key, preview)}：\n${text}` : `${indent}${fieldName(key, preview)}：${text.trim()}`;
    }).join("\n");
  }
  return String(value);
};
const valueText = (value: unknown, preview?: AgentActionPreview, field: string | undefined = ""): string => readableValue(value, preview, field ?? "");
const parameterLabel = (field: string, preview?: AgentActionPreview) => fieldName(field, preview);
// 501634（tgn 11-05）：确认窗口里的信息跟页面一致：没有中文名、值也不是中文的内部参数，和换不成案号、名称的编号不显示（执行照原样）。
const isIdField = (field: string) => field === "id" || /(_id|_ids|Ids)$/.test(field);
const isInternalParameter = (field: string, value: unknown, preview?: AgentActionPreview) => {
  if (isIdField(field)) {
    const items = Array.isArray(value) ? value : [value];
    return !items.length || items.some((item) => codeValue(field, item, preview) === item);
  }
  return fieldName(field, preview) === "其他信息" && !hasChinese(readableValue(value, preview, field));
};
const visibleParameterEntries = (values: Record<string, unknown>, preview?: AgentActionPreview) => Object.entries(values)
  .filter(([field, value]) => !HIDDEN_PARAMETER_FIELDS.has(field) && !isInternalParameter(field, value, preview));
const hiddenParameterCount = (values: Record<string, unknown>, preview?: AgentActionPreview) => Object.entries(values)
  .filter(([field, value]) => !HIDDEN_PARAMETER_FIELDS.has(field) && isInternalParameter(field, value, preview)).length;
/** 501634：老卡片的摘要里“案件ID：数字”换成案号，去掉“其他信息：编号/代码”。 */
export const readableAgentSummary = (summary: string, target?: string): string => userFacingAgentText(String(summary || ""))
  .replace(/案件ID[：:]\s*\d+/g, target ? `案号：${target}` : "")
  .replace(/[；;，,]?\s*其他信息[：:]\s*[A-Za-z0-9_\-.:/]+(?=[；;，,）)]|$)/g, "")
  .replace(/（[；;，,]\s*/g, "（").replace(/（\s*）/g, "");

/** 将模型遗留的技术字段转换为用户可读的中文，避免在聊天和确认标题中暴露接口字段。 */
export const userFacingAgentText = (value: string): string => Object.entries(USER_FACING_FIELD_NAMES).reduce(
  (text, [field, label]) => text.replace(new RegExp(`\\b${field}\\b`, "g"), label),
  value,
).replace(/path\s*参数/g, "相关信息").replace(/body\s*参数/g, "确认信息").replace(/query\s*参数/g, "相关信息").replace(/files\s*参数/g, "附件信息");

export const agentOperationName = (action: AgentApprovalAction) => userFacingAgentText(action.preview?.operation_name || ACTION_TYPE_NAMES[action.type] || action.summary);

export const agentOperationMessage = (value: unknown): string => {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(agentOperationMessage).join("；");
  if (value !== null && typeof value === "object") {
    const details = value as Record<string, unknown>;
    for (const field of ["error", "detail", "message", "msg"]) {
      if (details[field] !== undefined && details[field] !== null) return agentOperationMessage(details[field]);
    }
  }
  return JSON.stringify(value) ?? String(value);
};

/** fetch 失败时只取后端的中文说明（detail），不把 {"detail": ...} 原样显示给用户。 */
export const responseErrorMessage = async (response: Response, defaultMessage: string): Promise<string> => {
  try {
    const payload = (typeof response.text === "function" ? JSON.parse(await response.text()) : await response.json()) as unknown;
    if (payload !== null && typeof payload === "object") {
      const detail = (payload as Record<string, unknown>).detail ?? (payload as Record<string, unknown>).message;
      if (detail !== undefined && detail !== null && detail !== "") return agentOperationMessage(detail);
    }
  } catch { /* 非 JSON（如网关错误页）用默认提示。 */ }
  return defaultMessage;
};

export const agentOperationError = (error: unknown, defaultMessage: string): string => {
  if (isAxiosError(error) && error.response?.data?.detail !== undefined) {
    return agentOperationMessage(error.response.data.detail);
  }
  return error instanceof Error ? error.message : defaultMessage;
};

export const hasAgentOperationPreview = (action: AgentApprovalAction) => action.type !== "mcp.call" || Boolean(
  action.payload?.request_id && action.preview?.operation_name && action.preview.method && action.preview.path && action.preview.params && action.preview.requires_confirmation === true,
);

const ParameterValues = ({ values, preview }: { values: Record<string, unknown>; preview?: AgentActionPreview }) => <div className="agent-action-create">
  {visibleParameterEntries(values, preview).map(([field, value]) => <div key={field}>
    <strong style={{ overflowWrap: "anywhere" }}>{parameterLabel(field, preview)}</strong>
    <span style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{valueText(value, preview, field)}</span>
  </div>)}
</div>;

// 501634（tgn 11-05）：每个要改的字段一行“字段：原值 → 新值”，原来没有值写“（空）”；没变的不列，只说保持不变几项。
const isEmptyValue = (value: unknown) => value === undefined || value === null || value === "" || (Array.isArray(value) && !value.length);
const sameValue = (a: unknown, b: unknown) => (isEmptyValue(a) && isEmptyValue(b)) || JSON.stringify(a) === JSON.stringify(b);
const changeText = (value: unknown, preview: AgentActionPreview | undefined, field: string) => isEmptyValue(value) ? "（空）" : valueText(value, preview, field);
// 501634（tgn 11-05 07:47）：同一批人原来存的是姓名、这次写的是账号（郝蕴,鲍宇琳 → haoyun,baoyulin），显示成姓名后一样就算没变。
const shownKey = (text: string) => text.split(/[,，、;；\s]+/).filter(Boolean).join("、");
const sameShown = (change: { field: string; before?: unknown; after: unknown }, preview?: AgentActionPreview) => sameValue(change.before, change.after)
  || shownKey(changeText(change.before, preview, change.field)) === shownKey(changeText(change.after, preview, change.field));
type ChangeRow = { field: string; before?: unknown; before_read?: boolean; after: unknown };
const ChangeLines = ({ changes, preview }: { changes: ChangeRow[]; preview?: AgentActionPreview }) => {
  const visible = changes.filter((change) => !HIDDEN_PARAMETER_FIELDS.has(change.field) && !isInternalParameter(change.field, change.after, preview));
  const changed = visible.filter((change) => change.before_read !== true || !sameValue(change.before, change.after));
  const unchanged = visible.length - changed.length;
  return <section className="agent-action-changes">
    <strong>修改内容</strong>
    {changed.length ? changed.map((change) => <div key={change.field} className="agent-action-change-line" style={{ overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}>
      <b>{parameterLabel(change.field, preview)}</b>：{change.before_read === true ? changeText(change.before, preview, change.field) : "（未读取原值）"} → {changeText(change.after, preview, change.field)}
    </div>) : <div>没有字段发生变化</div>}
    {unchanged > 0 && <small className="agent-action-hidden-note">其余 {unchanged} 项保持不变。</small>}
  </section>;
};

/** 501634（tgn 11-06 00:01）：确认窗口的表格行。修改：只列要改的字段“字段 / 现状 / 改为”；新增：“字段 / 内容”。
 *  值用中文（案号、姓名、部门名），内部参数、编号、英文不出现。 */
export type AgentConfirmTable = { mode: "change" | "create"; rows: { field: string; label: string; before?: string; after: string }[] };
export const agentConfirmTable = (action: AgentApprovalAction): AgentConfirmTable => {
  const preview = action.preview;
  const label = (field: string) => parameterLabel(field, preview);
  const keep = (field: string, value: unknown) => !HIDDEN_PARAMETER_FIELDS.has(field) && !isInternalParameter(field, value, preview);
  if (!preview?.create && preview?.changes?.length) {
    const rows = preview.changes
      .filter((change) => keep(change.field, change.after) && (change.before_read !== true || !sameShown(change, preview)))
      .map((change) => ({ field: change.field, label: label(change.field),
        before: change.before_read === true ? changeText(change.before, preview, change.field) : "（未读取）",
        after: changeText(change.after, preview, change.field) }));
    return { mode: "change", rows };
  }
  const values = preview?.create || (preview?.params?.body && typeof preview.params.body === "object" && !Array.isArray(preview.params.body)
    ? preview.params.body as Record<string, unknown> : {});
  const rows = Object.entries(values).filter(([field, value]) => keep(field, value) && !isEmptyValue(value))
    .map(([field, value]) => ({ field, label: label(field), after: changeText(value, preview, field) }));
  if (typeof preview?.params?.steps === "string" && preview.params.steps.trim()) rows.push({ field: "steps", label: "办理步骤", after: preview.params.steps.trim() });
  return { mode: "create", rows };
};
/** 501634（tgn 11-05 07:22）：确认窗口标题不写案号（智能体就在本案里），只写这次动了哪一块，
 *  例如“修改/编辑确认：修改诉讼标的”“修改/编辑确认：修改案件基本信息、经办律师信息”；新增写“新增确认：新增××”。 */
export const agentConfirmHeadline = (action: AgentApprovalAction) => {
  const name = agentOperationName(action) || "智能体操作";
  if (agentConfirmTable(action).mode === "change") {
    const sections = (action.preview?.sections || []).map((item) => String(item || "").trim()).filter(Boolean);
    const what = sections.length ? sections.join("、") : name.replace(/^(修改|编辑|更新|变更)/, "") || "案件信息";
    return `修改/编辑确认：修改${what}`;
  }
  return /^(新增|新建|创建|添加)/.test(name) ? `新增确认：${name}` : `操作确认：${name}`;
};

// 卡片上的选择按确认请求编号记住；各处“批准”按钮提交时带上（agentChoiceBody），没选时提示（agentChoiceMissing）。
const AGENT_CHOICES = new Map<string, string | number>();
const choiceKey = (action: AgentApprovalAction) => String((action.payload as { request_id?: unknown } | undefined)?.request_id || action.id);
export const agentChoiceMissing = (action: AgentApprovalAction): string => {
  const choice = action.preview?.choice;
  return choice?.field && !AGENT_CHOICES.has(choiceKey(action)) ? `请先在卡片上选择${choice.label || "一项"}` : "";
};
export const agentChoiceBody = (action: AgentApprovalAction): { choice?: Record<string, string | number> } => {
  const choice = action.preview?.choice;
  const value = AGENT_CHOICES.get(choiceKey(action));
  return choice?.field && value !== undefined ? { choice: { [choice.field]: value } } : {};
};

export function AgentChoice({ action }: { action: AgentApprovalAction }) {
  const choice = action.preview?.choice;
  const [value, setValue] = useState<string | number | undefined>(() => AGENT_CHOICES.get(choiceKey(action)));
  if (!choice?.field || !choice.options?.length) return null;
  return <section className="agent-action-choice">
    <strong>请选择{choice.label || "一项"}（选了才能确认）</strong>
    <Radio.Group value={value} onChange={(event) => { AGENT_CHOICES.set(choiceKey(action), event.target.value); setValue(event.target.value); }}>
      <Space direction="vertical">
        {choice.options.map((item) => <Radio key={String(item.value)} value={item.value} style={{ whiteSpace: "normal" }}>{userFacingAgentText(item.label)}</Radio>)}
      </Space>
    </Radio.Group>
  </section>;
}

export function AgentOperationPreview({ action, target }: { action: AgentApprovalAction; target?: string }) {
  const preview = action.preview;
  return <div className="agent-action-approval" data-testid="agent-action-approval">
    <div className="agent-action-summary" style={{ overflowWrap: "anywhere" }}>
      <Tag color="processing" style={{ whiteSpace: "normal", maxWidth: "100%" }}>{agentOperationName(action)}</Tag>
      <strong>{readableAgentSummary(action.summary, target)}</strong>
      {(preview?.target || target) && <small>目标：{userFacingAgentText(String(preview?.target || target))}</small>}
    </div>
    <div className="agent-action-warning">确认后才会执行写入，仍须通过当前账号原有权限、数据范围与业务审批校验。聊天回复不作为确认。</div>
    {!hasAgentOperationPreview(action) && <Alert type="error" showIcon title="操作参数未读取，不能确认执行" />}
    <AgentChoice action={action} />
    {preview?.original_values && !/^\s*[\[{]/.test(preview.original_values) && <Descriptions size="small" bordered column={1} styles={{ content: { overflowWrap: "anywhere", whiteSpace: "pre-wrap" } }}>
      <Descriptions.Item label="当前信息">{userFacingAgentText(preview.original_values)}</Descriptions.Item>
    </Descriptions>}
    {preview?.params && Object.entries(preview.params).map(([group, value]) => {
      // 501634：有逐字段“原值 → 新值”时，提交的字段不再重复列一遍。
      if (group === "body" && !preview?.create && preview?.changes?.length) return null;
      const objectValue = value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
      if (objectValue && !visibleParameterEntries(objectValue, preview).length) return null;
      return <section key={group}>
        <strong>{PARAMETER_GROUP_NAMES[group] || "确认信息"}</strong>
        {objectValue
          ? <><ParameterValues values={objectValue} preview={preview} />
            {hiddenParameterCount(objectValue, preview) > 0 && <small className="agent-action-hidden-note">另有 {hiddenParameterCount(objectValue, preview)} 项系统内部参数未显示，执行时照原样使用。</small>}</>
          : <div style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{valueText(value, preview)}</div>}
      </section>;
    })}
    {preview?.create && <section><strong>确认信息</strong><ParameterValues values={preview.create} preview={preview} /></section>}
    {!preview?.create && !!preview?.changes?.length && <ChangeLines changes={preview.changes} preview={preview} />}
    {!preview?.params && !preview?.create && !preview?.changes?.length && action.payload && <section>
      <strong>确认信息</strong><ParameterValues values={action.payload} preview={preview} />
    </section>}
  </div>;
}
