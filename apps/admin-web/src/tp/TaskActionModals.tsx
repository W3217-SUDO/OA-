import {
  Alert,
  Button,
  DatePicker,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Select,
  Space,
  Table,
  Tag,
} from "antd";
import type { FormInstance } from "antd";
import type {
  TaskRow,
  DirectoryUser,
  HistoryItem,
  CaseRecord,
  DialogAction,
  FeeAction,
  FeeSubtype,
  CaseBatchAction,
  TaskBatchLifecycleAction,
} from "./types";
import {
  formatTaskScheduleTime,
  formatTaskDateTime,
  statusColors,
  taskEndedAt,
  taskStartedAt,
  visiblePersonName,
} from "./constants";

// ─── Handoff Modal ────────────────────────────────────────────────────────

export interface HandoffModalProps {
  handoff: TaskRow | null;
  handoffForm: FormInstance;
  handoffDirectory: DirectoryUser[];
  handoffDirectoryLoading: boolean;
  actionSubmitting: boolean;
  onOk: () => void;
  onCancel: () => void;
}

export function HandoffModal(props: HandoffModalProps) {
  const { handoff, handoffForm, handoffDirectory, handoffDirectoryLoading, actionSubmitting, onOk, onCancel } = props;
  return (
    <Modal
      open={Boolean(handoff)}
      title={`任务转交：${handoff?.serial_no || ""}`}
      okText="确认转交"
      cancelText="取消"
      confirmLoading={actionSubmitting}
      onOk={onOk}
      onCancel={onCancel}
    >
      <Alert
        type="warning"
        showIcon
        message="转交后 5 天内接收人未开始，系统按交接规则自动完成。"
      />
      <Form form={handoffForm} layout="vertical" style={{ marginTop: 18 }}>
          <div className="form-grid">
            <Form.Item label="任务开始时间">
              <Input value={formatTaskDateTime(handoff?.start_at || handoff?.created_at)} disabled />
            </Form.Item>
            <Form.Item label="任务结束时间">
              <Input value={formatTaskDateTime(handoff?.end_at || handoff?.deadline)} disabled />
            </Form.Item>
          </div>
        <Form.Item
          label="接收人"
          name="recipient"
          rules={[{ required: true, message: "请选择接收人" }]}
        >
            <Select
              showSearch
              loading={handoffDirectoryLoading}
              optionFilterProp="label"
              placeholder="输入姓名或部门搜索"
              options={handoffDirectory.map((user) => ({
                value: user.username,
                label: `${user.display_name || user.username}（${user.department || "未设置部门"}）`,
              }))}
            />
        </Form.Item>
        <Form.Item label="转交说明" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ─── Dialog Modal (reject / resend) ──────────────────────────────────────

export interface DialogModalProps {
  dialog: { row: TaskRow; action: DialogAction } | null;
  dialogForm: FormInstance;
  actionSubmitting: boolean;
  onOk: () => void;
  onCancel: () => void;
}

export function DialogModal(props: DialogModalProps) {
  const { dialog, dialogForm, actionSubmitting, onOk, onCancel } = props;
  return (
    <Modal
      open={Boolean(dialog)}
      title={dialog?.action === "reject" ? "拒绝任务" : "重新派发任务"}
      okText="确认"
      cancelText="取消"
      confirmLoading={actionSubmitting}
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={dialogForm} layout="vertical">
        {dialog?.action === "resend" && (
          <Form.Item
            label="新负责人"
            name="recipient"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
        )}
        <Form.Item
          label={dialog?.action === "reject" ? "拒绝理由" : "派发说明"}
          name="comment"
          rules={[{ required: true }]}
        >
          <Input.TextArea rows={4} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ─── Task Batch Lifecycle Modal ──────────────────────────────────────────

export interface TaskBatchModalProps {
  taskBatchAction: TaskBatchLifecycleAction | null;
  taskBatchForm: FormInstance;
  selectedCount: number;
  actionSubmitting: boolean;
  labels: Record<TaskBatchLifecycleAction, string>;
  onOk: () => void;
  onCancel: () => void;
}

export function TaskBatchModal(props: TaskBatchModalProps) {
  const {
    taskBatchAction,
    taskBatchForm,
    selectedCount,
    actionSubmitting,
    labels,
    onOk,
    onCancel,
  } = props;
  return (
    <Modal
      open={Boolean(taskBatchAction)}
      title={`${
        taskBatchAction ? labels[taskBatchAction] : "批量任务流转"
      }（已选 ${selectedCount} 条）`}
      okText="确认执行"
      cancelText="取消"
      confirmLoading={actionSubmitting}
      onOk={onOk}
      onCancel={onCancel}
      destroyOnHidden
    >
      <Alert
        type={taskBatchAction === "withdraw" ? "warning" : "info"}
        showIcon
        message={
          taskBatchAction === "handoff"
            ? "所有任务将转交给同一接收人；交接后 5 天内未重新开始会自动完成。"
            : taskBatchAction === "withdraw"
              ? "仅任务发起人或管理员可撤回；任一任务不符合条件时整批不会提交。"
              : taskBatchAction === "confirm"
                ? "仅任务发起人或管理员可验收待确认任务；任一任务不符合条件时整批不会提交。"
                : "系统将逐条核验负责人、状态和权限；任一任务不符合条件时整批不会提交。"
        }
        style={{ marginBottom: 16 }}
      />
      <Form form={taskBatchForm} layout="vertical">
        {taskBatchAction === "handoff" && (
          <Form.Item
            label="接收人"
            name="recipient"
            rules={[{ required: true, message: "请输入接收人" }]}
          >
            <Input />
          </Form.Item>
        )}
        <Form.Item
          label={taskBatchAction === "withdraw" ? "撤回原因" : "操作说明"}
          name="comment"
          rules={
            taskBatchAction === "withdraw"
              ? [{ required: true, message: "请填写撤回原因" }]
              : []
          }
        >
          <Input.TextArea
            rows={4}
            placeholder={
              taskBatchAction === "withdraw"
                ? "请填写撤回原因"
                : "可选，写入每条任务的流转记录"
            }
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ─── Fee Modal ───────────────────────────────────────────────────────────

export interface FeeModalProps {
  feeAction: FeeAction | null;
  feeSubtype: FeeSubtype | null;
  feeForm: FormInstance;
  selected: TaskRow | null;
  actionSubmitting: boolean;
  labels: { lawFee: string; platformFee: string; internalFee: string };
  onOk: () => void;
  onCancel: () => void;
  onOpenCommunication: (row: TaskRow) => void;
  onOpenCaseDetail: (row: TaskRow) => void;
}

export function FeeModal(props: FeeModalProps) {
  const {
    feeAction,
    feeSubtype,
    feeForm,
    selected,
    actionSubmitting,
    labels,
    onOk,
    onCancel,
    onOpenCommunication,
    onOpenCaseDetail,
  } = props;
  return (
    <Modal
      open={Boolean(feeAction)}
      title={
        feeAction
          ? `${labels[feeAction]}${feeSubtype ? ` - ${feeSubtype}` : ""}`
          : "新增费用"
      }
      okText="保存并提交审批"
      cancelText="取消"
      confirmLoading={actionSubmitting}
      onOk={onOk}
      onCancel={onCancel}
      destroyOnHidden
    >
      <Alert
        type="info"
        showIcon
        message={
          <Space size={4}>
            关联任务：
            {selected ? (
              <Button
                className="business-relation-link"
                type="link"
                onClick={() => onOpenCommunication(selected)}
              >
                {selected.serial_no}
              </Button>
            ) : (
              "-"
            )}
            ；关联案件：
            {selected?.case_no ? (
              <Button
                className="business-relation-link"
                type="link"
                onClick={() => onOpenCaseDetail(selected)}
              >
                {selected.case_no}
              </Button>
            ) : (
              "-"
            )}
          </Space>
        }
        style={{ marginBottom: 16 }}
      />
      <Form form={feeForm} layout="vertical">
        <div className="form-grid">
          <Form.Item
            label="费用金额"
            name="amount"
            rules={[{ required: true, message: "请输入费用金额" }]}
          >
            <InputNumber
              min={0.01}
              precision={2}
              style={{ width: "100%" }}
              addonAfter="元"
            />
          </Form.Item>
          <Form.Item label="费用日期" name="expense_date" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="申请人" name="applicant" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </div>
        <Form.Item
          label="费用说明"
          name="description"
          rules={[{ required: true, message: "请填写费用说明" }]}
        >
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ─── Case Batch Modal ────────────────────────────────────────────────────

export interface CaseBatchModalProps {
  caseBatchAction: CaseBatchAction | null;
  batchForm: FormInstance;
  selectedCaseNos: string[];
  actionSubmitting: boolean;
  labels: Record<CaseBatchAction, string>;
  onOk: () => void;
  onCancel: () => void;
}

export function CaseBatchModal(props: CaseBatchModalProps) {
  const {
    caseBatchAction,
    batchForm,
    selectedCaseNos,
    actionSubmitting,
    labels,
    onOk,
    onCancel,
  } = props;
  return (
    <Modal
      open={Boolean(caseBatchAction)}
      title={`${
        caseBatchAction ? labels[caseBatchAction] : "批量修改"
      }（已选 ${selectedCaseNos.length} 个案件）`}
      okText="确认修改"
      cancelText="取消"
      confirmLoading={actionSubmitting}
      onOk={onOk}
      onCancel={onCancel}
      destroyOnHidden
    >
      <Alert
        type="warning"
        showIcon
        message={`将同时修改案件：${selectedCaseNos.join("、")}`}
        style={{ marginBottom: 16 }}
      />
      <Form form={batchForm} layout="vertical">
        {caseBatchAction === "hearing_lawyer" && (
          <Form.Item
            label="开庭律师"
            name="hearing_lawyer"
            rules={[{ required: true, message: "请输入开庭律师" }]}
          >
            <Input />
          </Form.Item>
        )}
        {caseBatchAction === "handling_lawyers" && (
          <Form.Item
            label="经办律师"
            name="handling_lawyers"
            rules={[{ required: true, message: "请输入经办律师" }]}
          >
            <Select mode="tags" tokenSeparators={[",", "，"]} />
          </Form.Item>
        )}
        {caseBatchAction === "assistant" && (
          <Form.Item
            label="律师助理"
            name="assistant"
            rules={[{ required: true, message: "请输入律师助理" }]}
          >
            <Input />
          </Form.Item>
        )}
        {caseBatchAction === "case_stage" && (
          <Form.Item
            label="案件阶段"
            name="case_stage"
            rules={[{ required: true, message: "请输入案件阶段" }]}
          >
            <Input />
          </Form.Item>
        )}
        <Form.Item label="修改说明" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ─── Document Modal ──────────────────────────────────────────────────────

export interface DocumentModalProps {
  documentAction: "authorization" | "lawFirmLetter" | "identity" | "settlement" | null;
  documentForm: FormInstance;
  actionSubmitting: boolean;
  labels: { authorization: string; lawFirmLetter: string; identity: string; settlement: string };
  onOk: () => void;
  onCancel: () => void;
}

export function DocumentModal(props: DocumentModalProps) {
  const { documentAction, documentForm, actionSubmitting, labels, onOk, onCancel } = props;
  return (
    <Modal
      open={Boolean(documentAction)}
      title={documentAction ? `生成${labels[documentAction]}` : "生成文书"}
      okText="生成并下载"
      cancelText="取消"
      confirmLoading={actionSubmitting}
      onOk={onOk}
      onCancel={onCancel}
      destroyOnHidden
    >
      <Alert
        type="info"
        showIcon
        message="系统将使用关联案件资料和对应模板生成 Word 文书；Dify 未配置时仍会生成可编辑的字段提纲。"
        style={{ marginBottom: 16 }}
      />
      <Form form={documentForm} layout="vertical">
        <Form.Item label="文书标题" name="title" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item label="生成要求" name="instruction">
          <Input.TextArea rows={4} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ─── Case Context Modal (case tasks / case logs) ─────────────────────────

export interface CaseContextModalProps {
  caseContext: { mode: "tasks" | "logs"; record: CaseRecord } | null;
  caseTasks: TaskRow[];
  caseHistory: HistoryItem[];
  caseTaskContextMeta: { total: number; page: number; pageSize: number; pages: number };
  caseContextLoading: boolean;
  onCancel: () => void;
  onCaseTaskPageChange: (page: number, pageSize: number) => void;
}

export function CaseContextModal(props: CaseContextModalProps) {
  const {
    caseContext,
    caseTasks,
    caseHistory,
    caseTaskContextMeta,
    caseContextLoading,
    onCancel,
    onCaseTaskPageChange,
  } = props;

  const caseTaskContextPagination = {
    current: caseTaskContextMeta.page,
    pageSize: caseTaskContextMeta.pageSize,
    total: caseTaskContextMeta.total,
    showSizeChanger: true,
    pageSizeOptions: [15, 30, 50, 100, 200],
    showTotal: (total: number) => `共 ${total} 条`,
    onChange: onCaseTaskPageChange,
  };

  return (
    <Modal
      width={900}
      open={Boolean(caseContext)}
      title={`${
        caseContext?.mode === "tasks" ? "案件任务" : "案件日志"
      }：${caseContext?.record.serial_no || ""}`}
      footer={<Button onClick={onCancel}>关闭</Button>}
      onCancel={onCancel}
      loading={caseContextLoading}
    >
      {caseContext?.mode === "tasks" ? (
        <Table<TaskRow>
          className="task-case-context-table"
          rowKey="id"
          size="small"
          pagination={caseTaskContextPagination}
          tableLayout="fixed"
          scroll={{ x: 820 }}
          dataSource={caseTasks}
          locale={{ emptyText: "当前案件暂无任务" }}
          columns={[
            { title: "任务编号", dataIndex: "serial_no", width: 200, ellipsis: true },
            { title: "任务名称", dataIndex: "title", width: 280, ellipsis: true },
            {
              title: "负责人",
              dataIndex: "owner",
              width: 100,
              render: (_: string, row: TaskRow) =>
                visiblePersonName(row.owner_display_name),
            },
            {
              title: "开始时间",
              key: "started_at",
              width: 135,
              render: (_: unknown, row: TaskRow) =>
                formatTaskScheduleTime(taskStartedAt(row)) || "—",
            },
            {
              title: "结束时间",
              dataIndex: "deadline",
              width: 135,
              render: (_: string, row: TaskRow) =>
                formatTaskScheduleTime(taskEndedAt(row)) || "—",
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 95,
              render: (value: string) => (
                <Tag color={statusColors[value] || "blue"}>{value}</Tag>
              ),
            },
          ]}
        />
      ) : (
        <List
          className="task-history"
          dataSource={caseHistory}
          locale={{ emptyText: "当前案件暂无流转日志" }}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <Space>
                    <Tag>{item.action}</Tag>
                    <b>{visiblePersonName(item.operator_display_name)}</b>
                    <span>{new Date(item.created_at).toLocaleString("zh-CN")}</span>
                  </Space>
                }
                description={
                  <>
                    <div>
                      {item.from_status && item.to_status
                        ? `${item.from_status} → ${item.to_status}`
                        : ""}
                    </div>
                    <p>{item.comment || "-"}</p>
                  </>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Modal>
  );
}
