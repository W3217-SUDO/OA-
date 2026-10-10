import { Alert, Descriptions, Table, Tag } from "antd";
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
};
const PARAMETER_GROUP_NAMES: Record<string, string> = {
  path: "路径参数", query: "查询参数", body: "请求正文", files: "附件参数",
};
const valueText = (value: unknown): string => {
  if (value === undefined) return "未读取";
  if (value === null) return "空值 (null)";
  if (value === "") return "空字符串";
  return typeof value === "object" ? JSON.stringify(value, null, 2) : String(value);
};
const parameterLabel = (field: string) => ACTION_FIELD_NAMES[field] ? `${ACTION_FIELD_NAMES[field]} (${field})` : field;

export const agentOperationName = (action: AgentApprovalAction) => action.preview?.operation_name || ACTION_TYPE_NAMES[action.type] || action.summary;

export const agentOperationError = (error: unknown, defaultMessage: string): string => {
  if (isAxiosError(error) && error.response?.data?.detail !== undefined) {
    const detail = error.response.data.detail;
    return typeof detail === "string" ? detail : JSON.stringify(detail);
  }
  return error instanceof Error ? error.message : defaultMessage;
};

export const hasAgentOperationPreview = (action: AgentApprovalAction) => action.type !== "mcp.call" || Boolean(
  action.payload?.request_id && action.preview?.operation_name && action.preview.method && action.preview.path && action.preview.params && action.preview.requires_confirmation === true,
);

const ParameterValues = ({ values }: { values: Record<string, unknown> }) => <div className="agent-action-create">
  {Object.entries(values).map(([field, value]) => <div key={field}>
    <strong style={{ overflowWrap: "anywhere" }}>{parameterLabel(field)}</strong>
    <span>{valueText(value)}</span>
  </div>)}
</div>;

export function AgentOperationPreview({ action, target }: { action: AgentApprovalAction; target?: string }) {
  const preview = action.preview;
  const requestId = action.payload?.request_id;
  return <div className="agent-action-approval" data-testid="agent-action-approval">
    <div className="agent-action-summary" style={{ overflowWrap: "anywhere" }}>
      <Tag color="processing" style={{ whiteSpace: "normal", maxWidth: "100%" }}>{agentOperationName(action)}</Tag>
      <strong>{action.summary}</strong>
      {(preview?.target || target) && <small>目标：{preview?.target || target}</small>}
    </div>
    <div className="agent-action-warning">确认后才会执行写入，仍须通过当前账号原有权限、数据范围与业务审批校验。聊天回复不作为确认。</div>
    {!hasAgentOperationPreview(action) && <Alert type="error" showIcon title="操作参数未读取，不能确认执行" />}
    {preview?.method && preview.path && <Descriptions size="small" bordered column={1} styles={{ content: { overflowWrap: "anywhere", whiteSpace: "pre-wrap" } }}>
      {requestId !== undefined && <Descriptions.Item label="请求 ID">{valueText(requestId)}</Descriptions.Item>}
      <Descriptions.Item label="接口">{preview.method} {preview.path}</Descriptions.Item>
      {preview.original_values && <Descriptions.Item label="原值读取">{preview.original_values}</Descriptions.Item>}
    </Descriptions>}
    {preview?.params && Object.entries(preview.params).map(([group, value]) => <section key={group}>
      <strong>{PARAMETER_GROUP_NAMES[group] || group}</strong>
      {value !== null && typeof value === "object" && !Array.isArray(value)
        ? Object.keys(value).length ? <ParameterValues values={value as Record<string, unknown>} /> : <div>{valueText(value)}</div>
        : <div style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{valueText(value)}</div>}
    </section>)}
    {preview?.create && <section><strong>提交参数</strong><ParameterValues values={preview.create} /></section>}
    {!preview?.create && !!preview?.changes?.length && <Table
      size="small" bordered pagination={false} rowKey="field" dataSource={preview.changes}
      scroll={{ x: 480 }}
      columns={[
        { title: "字段", dataIndex: "field", width: 130, render: (field: string) => parameterLabel(field) },
        { title: "修改前", dataIndex: "before", render: (value: unknown, change: { before_read?: boolean }) => <span style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{change.before_read === true ? valueText(value) : "未读取"}</span> },
        { title: "修改后", dataIndex: "after", render: (value: unknown) => <span style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{valueText(value)}</span> },
      ]}
    />}
    {!preview?.params && !preview?.create && !preview?.changes?.length && action.payload && <section>
      <strong>提交参数</strong><ParameterValues values={action.payload} />
    </section>}
  </div>;
}
