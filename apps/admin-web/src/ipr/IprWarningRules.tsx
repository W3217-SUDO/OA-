import {
Alert,
Button,
Card,
Checkbox,
Drawer,
Form,
Input,
InputNumber,
Modal,
Select,
Space,
Table,
Tag,
} from "antd";
import type {
IprReminderEventOption,
IprWarning,
IprWarningRule,
} from "./types";

interface IprWarningRulesProps {
  isAdmin: boolean;
  warningWorkbenchOpen: boolean;
  warningRuleEditorOpen: boolean;
  warningRules: IprWarningRule[];
  warnings: IprWarning[];
  warningLoading: boolean;
  warningRulesLoading: boolean;
  warningTotal: number;
  warningUnread: number;
  warningPage: number;
  warningStatus: "" | "未读" | "已读" | "已处理";
  warningCaseKind: "" | "专利" | "商标";
  editingWarningRule: IprWarningRule | null;
  processingWarning: IprWarning | null;
  warningRuleForm: any;
  warningProcessForm: any;
  canManageWarningRules: boolean;
  reminderTypeEventOptions: IprReminderEventOption[];
  onCloseWorkbench: () => void;
  onNavigateMessages: () => void;
  onGenerateWarnings: () => void;
  onLoadWarnings: (page?: number) => void;
  onLoadWarningRules: () => void;
  onOpenRuleEditor: (rule?: IprWarningRule) => void;
  onCloseRuleEditor: () => void;
  onSaveRule: () => void;
  onDeleteRule: (rule: IprWarningRule) => void;
  onStatusChange: (status: "" | "未读" | "已读" | "已处理") => void;
  onCaseKindChange: (kind: "" | "专利" | "商标") => void;
  onMarkRead: (warning: IprWarning) => void;
  onOpenWarningCase: (warning: IprWarning) => void;
  onOpenProcess: (warning: IprWarning) => void;
  onCloseProcess: () => void;
  onProcessWarning: () => void;
}

export function IprWarningRules({
  isAdmin,
  warningWorkbenchOpen,
  warningRuleEditorOpen,
  warningRules,
  warnings,
  warningLoading,
  warningRulesLoading,
  warningTotal,
  warningUnread,
  warningPage,
  warningStatus,
  warningCaseKind,
  editingWarningRule,
  processingWarning,
  warningRuleForm,
  warningProcessForm,
  canManageWarningRules,
  reminderTypeEventOptions,
  onCloseWorkbench,
  onNavigateMessages,
  onGenerateWarnings,
  onLoadWarnings,
  onLoadWarningRules,
  onOpenRuleEditor,
  onCloseRuleEditor,
  onSaveRule,
  onDeleteRule,
  onStatusChange,
  onCaseKindChange,
  onMarkRead,
  onOpenWarningCase,
  onOpenProcess,
  onCloseProcess,
  onProcessWarning,
}: IprWarningRulesProps) {
  return (
    <>
      <Drawer
        open={warningWorkbenchOpen}
        title={
          <Space>
            案件预警工作台
            {warningUnread ? (
              <Tag color="red">{warningUnread} 条未读</Tag>
            ) : null}
          </Space>
        }
        width={1120}
        onClose={onCloseWorkbench}
        extra={
          <Space>
            <Button onClick={onNavigateMessages}>通知中心</Button>
            <Button onClick={onGenerateWarnings}>刷新并生成</Button>
            {canManageWarningRules ? (
              <Button type="primary" onClick={() => onOpenRuleEditor()}>
                新建规则
              </Button>
            ) : null}
          </Space>
        }
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="规则按案件类型与时间节点生成预警"
          description="预警只显示当前登录人可查看且分配给本人的案件；打开、标已读和处理会同步通知中心。"
        />
        <Card size="small" title="预警规则" style={{ marginBottom: 16 }}>
          <Table<IprWarningRule>
            rowKey="id"
            size="small"
            loading={warningRulesLoading}
            dataSource={warningRules}
            pagination={false}
            scroll={{ x: 880 }}
            columns={[
              { title: "规则名称", dataIndex: "name", width: 180 },
              {
                title: "案件类型",
                dataIndex: "case_kind",
                width: 100,
                render: (value) => value || "全部",
              },
              {
                title: "案件子类型 / 阶段",
                width: 210,
                render: (_, row) =>
                  [row.case_type, row.case_phase]
                    .filter(Boolean)
                    .join(" / ") || "全部",
              },
              {
                title: "时间节点",
                width: 170,
                render: (_, row) =>
                  row.time_node === "reminder_deadline"
                    ? `提醒事项截止日${
                        row.event_type_id ? `（事件 #${row.event_type_id}）` : ""
                      }`
                    : "案件办理期限",
              },
              {
                title: "提前天数",
                dataIndex: "days_before",
                width: 100,
                render: (value) => `${value} 天`,
              },
              {
                title: "状态",
                dataIndex: "is_active",
                width: 90,
                render: (value) => (
                  <Tag color={value ? "green" : "default"}>
                    {value ? "启用" : "停用"}
                  </Tag>
                ),
              },
              {
                title: "操作",
                fixed: "right",
                width: 130,
                render: (_, row) =>
                  canManageWarningRules ? (
                    <Space size={0}>
                      <Button
                        type="link"
                        onClick={() => onOpenRuleEditor(row)}
                      >
                        编辑
                      </Button>
                      <Button
                        type="link"
                        danger
                        onClick={() => onDeleteRule(row)}
                      >
                        删除
                      </Button>
                    </Space>
                  ) : (
                    "—"
                  ),
              },
            ]}
          />
        </Card>
        <Card
          size="small"
          title={
            isAdmin ? "可见案件预警" : "我的案件预警"
          }
          extra={
            <Space>
              <Select
                value={warningStatus}
                onChange={(value) => onStatusChange(value)}
                style={{ width: 104 }}
                options={[
                  { value: "", label: "全部状态" },
                  { value: "未读", label: "未读" },
                  { value: "已读", label: "已读" },
                  { value: "已处理", label: "已处理" },
                ]}
              />
              <Select
                value={warningCaseKind}
                onChange={(value) => onCaseKindChange(value)}
                style={{ width: 104 }}
                options={[
                  { value: "", label: "全部类型" },
                  { value: "专利", label: "专利" },
                  { value: "商标", label: "商标" },
                ]}
              />
              <Button onClick={() => onLoadWarnings(1)}>查询</Button>
            </Space>
          }
        >
          <Table<IprWarning>
            rowKey="id"
            size="small"
            loading={warningLoading}
            dataSource={warnings}
            scroll={{ x: 1120 }}
            pagination={{
              current: warningPage,
              pageSize: 15,
              total: warningTotal,
              showSizeChanger: false,
              onChange: (nextPage) => onLoadWarnings(nextPage),
            }}
            columns={[
              {
                title: "状态",
                width: 88,
                render: (_, row) => (
                  <Tag
                    color={
                      row.status === "已处理"
                        ? "green"
                        : row.is_read
                          ? "blue"
                          : "red"
                    }
                  >
                    {row.status}
                  </Tag>
                ),
              },
              {
                title: "预警内容",
                dataIndex: "title",
                width: 210,
                ellipsis: true,
              },
              {
                title: "关联案件",
                width: 220,
                ellipsis: true,
                render: (_, row) => (
                  <Button type="link" onClick={() => onOpenWarningCase(row)}>
                    {row.case_no}｜{row.case_title}
                  </Button>
                ),
              },
              { title: "类型", dataIndex: "case_kind", width: 75 },
              { title: "到期日", dataIndex: "due_date", width: 112 },
              { title: "说明", dataIndex: "content", ellipsis: true },
              {
                title: "处理说明",
                dataIndex: "process_comment",
                width: 160,
                ellipsis: true,
                render: (value) => value || "—",
              },
              {
                title: "操作",
                fixed: "right",
                width: 150,
                render: (_, row) =>
                  true ? (
                    <Space size={0}>
                      {!row.is_read && (
                        <Button
                          type="link"
                          onClick={() => onMarkRead(row)}
                        >
                          标已读
                        </Button>
                      )}
                      {row.status !== "已处理" && (
                        <Button
                          type="link"
                          onClick={() => onOpenProcess(row)}
                        >
                          处理
                        </Button>
                      )}
                    </Space>
                  ) : (
                    "仅接收人可处理"
                  ),
              },
            ]}
          />
        </Card>
      </Drawer>

      <Modal
        open={warningRuleEditorOpen}
        title={
          editingWarningRule
            ? `编辑预警规则：${editingWarningRule.name}`
            : "新建案件预警规则"
        }
        width={680}
        onCancel={onCloseRuleEditor}
        onOk={onSaveRule}
        okText="保存"
      >
        <Form form={warningRuleForm} layout="vertical">
          <div className="form-grid">
            <Form.Item
              name="name"
              label="规则名称"
              rules={[{ required: true, message: "请输入规则名称" }]}
            >
              <Input maxLength={128} />
            </Form.Item>
            <Form.Item name="case_kind" label="案件类型">
              <Select
                allowClear
                options={[
                  { value: "专利", label: "专利" },
                  { value: "商标", label: "商标" },
                ]}
              />
            </Form.Item>
            <Form.Item name="case_type" label="案件子类型">
              <Input maxLength={128} />
            </Form.Item>
            <Form.Item name="case_phase" label="案件阶段">
              <Input maxLength={128} />
            </Form.Item>
            <Form.Item
              name="time_node"
              label="时间节点"
              rules={[{ required: true }]}
            >
              <Select
                options={[
                  { value: "case_deadline", label: "案件办理期限" },
                  { value: "reminder_deadline", label: "提醒事项截止日" },
                ]}
              />
            </Form.Item>
            <Form.Item
              noStyle
              shouldUpdate={(previous, current) =>
                previous.time_node !== current.time_node
              }
            >
              {({ getFieldValue }) =>
                getFieldValue("time_node") === "reminder_deadline" ? (
                  <Form.Item
                    name="event_type_id"
                    label="提醒事项类型"
                    rules={[
                      { required: true, message: "请选择提醒事项类型" },
                    ]}
                  >
                    <Select
                      options={[
                        { value: 0, label: "全部提醒事项类型" },
                        ...reminderTypeEventOptions.map((item) => ({
                          value: item.id,
                          label: item.name,
                        })),
                      ]}
                    />
                  </Form.Item>
                ) : (
                  <div />
                )
              }
            </Form.Item>
            <Form.Item
              name="days_before"
              label="提前预警天数"
              rules={[{ required: true, message: "请输入提前天数" }]}
            >
              <InputNumber
                min={0}
                max={3650}
                precision={0}
                style={{ width: "100%" }}
              />
            </Form.Item>
          </div>
          <Form.Item name="is_active" valuePropName="checked">
            <Checkbox>启用规则</Checkbox>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={!!processingWarning}
        title="处理案件预警"
        onCancel={onCloseProcess}
        onOk={onProcessWarning}
        okText="确认处理"
      >
        <p>{processingWarning?.title}</p>
        <Form form={warningProcessForm} layout="vertical">
          <Form.Item name="comment" label="处理说明">
            <Input.TextArea
              rows={4}
              maxLength={1000}
              placeholder="可选；会保留在预警处理记录中"
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
