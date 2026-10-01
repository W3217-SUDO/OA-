import { Alert, Button, DatePicker, Form, Input, Modal, Select } from "antd";
import Table from "../components/ResizableTable";
import dayjs from "dayjs";
import type { FinancePersonOption, SettlementContext, SettlementContextRow, SettlementTaskForm } from "./types";

export interface SettlementContextModalProps {
  context: SettlementContext | null;
  onClose: () => void;
  actionLoading: boolean;
  onSubmitLog: () => Promise<void>;
  onSubmitTask: () => Promise<void>;
  logContent: string;
  onLogContentChange: (value: string) => void;
  taskForm: SettlementTaskForm;
  onTaskFormChange: (form: SettlementTaskForm) => void;
  financePeople: FinancePersonOption[];
  rows: SettlementContextRow[];
  displayPersonName: (identity?: unknown, displayName?: unknown) => string;
}

export function SettlementContextModal({
  context: settlementContext,
  onClose,
  actionLoading: settlementActionLoading,
  onSubmitLog: submitSettlementLog,
  onSubmitTask: submitSettlementTask,
  logContent: settlementLogContent,
  onLogContentChange: setSettlementLogContent,
  taskForm: settlementTaskForm,
  onTaskFormChange: setSettlementTaskForm,
  financePeople,
  rows: settlementContextRows,
  displayPersonName: financePersonDisplayName,
}: SettlementContextModalProps) {
  return (
    <Modal
      width={900}
      open={Boolean(settlementContext)}
      title={
        settlementContext?.mode === "log-create"
          ? `新增案件日志（${settlementContext?.caseRecords.length || 0} 个案件）`
          : settlementContext?.mode === "task-create"
            ? `新增案件任务（${settlementContext?.caseRecords.length || 0} 个案件）`
            : `已选 ${settlementContext?.caseRecords.length || 0} 个案件｜${settlementContext?.mode === "tasks" ? "案件任务" : "案件日志"}`
      }
      footer={
        settlementContext?.mode === "log-create" ? (
          <>
            <Button onClick={() => onClose()}>取消</Button>
            <Button type="primary" loading={settlementActionLoading} onClick={() => void submitSettlementLog()}>保存日志</Button>
          </>
        ) : settlementContext?.mode === "task-create" ? (
          <>
            <Button onClick={() => onClose()}>取消</Button>
            <Button type="primary" loading={settlementActionLoading} onClick={() => void submitSettlementTask()}>创建任务</Button>
          </>
        ) : (
          <Button onClick={() => onClose()}>关闭</Button>
        )
      }
      onCancel={() => onClose()}
      destroyOnHidden
    >
      {settlementContext?.mode === "log-create" ? (
        <div>
          <Alert
            type="info"
            showIcon
            message={`将为以下 ${settlementContext?.caseRecords.length || 0} 个案件添加相同的日志：`}
            description={
              <div style={{ maxHeight: 120, overflowY: "auto", marginTop: 8 }}>
                {(settlementContext?.caseRecords || []).map((row: SettlementContext["caseRecords"][number]) => (
                  <div key={row.id} style={{ fontSize: 12, lineHeight: "20px" }}>
                    {row.data?.case_no || row.serial_no}
                  </div>
                ))}
              </div>
            }
            style={{ marginBottom: 16 }}
          />
          <Input.TextArea
            rows={8}
            value={settlementLogContent}
            onChange={(e) => setSettlementLogContent(e.target.value)}
            placeholder="请输入日志内容..."
          />
        </div>
      ) : settlementContext?.mode === "task-create" ? (
        <div>
          <Alert
            type="info"
            showIcon
            message={`将为以下 ${settlementContext?.caseRecords.length || 0} 个案件创建相同的任务：`}
            description={
              <div style={{ maxHeight: 120, overflowY: "auto", marginTop: 8 }}>
                {(settlementContext?.caseRecords || []).map((row: SettlementContext["caseRecords"][number]) => (
                  <div key={row.id} style={{ fontSize: 12, lineHeight: "20px" }}>
                    {row.data?.case_no || row.serial_no}
                  </div>
                ))}
              </div>
            }
            style={{ marginBottom: 16 }}
          />
          <Form layout="vertical">
            <Form.Item label="任务名称" required>
              <Input
                value={settlementTaskForm.title}
                onChange={(e) => setSettlementTaskForm({ ...settlementTaskForm, title: e.target.value })}
                placeholder="请输入任务名称"
              />
            </Form.Item>
            <div className="form-grid">
              <Form.Item label="负责人" required>
                <Select
                  showSearch
                  optionFilterProp="label"
                  value={settlementTaskForm.owner || undefined}
                  onChange={(val) => setSettlementTaskForm({ ...settlementTaskForm, owner: val })}
                  placeholder="请选择负责人"
                  options={financePeople.map((person) => ({ value: person.username, label: person.label }))}
                />
              </Form.Item>
              <Form.Item label="优先级">
                <Select
                  value={settlementTaskForm.priority}
                  onChange={(val) => setSettlementTaskForm({ ...settlementTaskForm, priority: val })}
                  options={[
                    { value: "紧急", label: "紧急" },
                    { value: "高", label: "高" },
                    { value: "普通", label: "普通" },
                    { value: "低", label: "低" },
                  ]}
                />
              </Form.Item>
            </div>
            <Form.Item label="截止日期" required>
              <DatePicker
                style={{ width: "100%" }}
                value={settlementTaskForm.deadline}
                onChange={(val) => setSettlementTaskForm({ ...settlementTaskForm, deadline: val })}
              />
            </Form.Item>
          </Form>
        </div>
      ) : (
        <Table
          rowKey="id"
          size="small"
          dataSource={settlementContextRows}
          pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
          locale={{
            emptyText:
              settlementContext?.mode === "tasks"
                ? "当前案件没有任务"
                : "当前案件没有日志",
          }}
          columns={
            settlementContext?.mode === "tasks"
              ? [
                  { title: "案号", dataIndex: "source_case_no", width: 150 },
                  { title: "任务编号", dataIndex: "serial_no", width: 150 },
                  { title: "任务名称", dataIndex: "title", width: 200 },
                  { title: "状态", dataIndex: "status", width: 90 },
                  { title: "负责人", dataIndex: "owner", width: 100, render: (value: string, row: SettlementContextRow) => financePersonDisplayName(value, row.owner_display_name) },
                  { title: "截止日期", dataIndex: "deadline", width: 120 },
                ]
              : [
                  { title: "案号", dataIndex: "source_case_no", width: 150 },
                  { title: "操作", dataIndex: "action", width: 130 },
                  {
                    title: "状态变化",
                    key: "status",
                    width: 150,
                    render: (_: unknown, row: SettlementContextRow) =>
                      `${row.from_status || "—"} → ${row.to_status || "—"}`,
                  },
                  { title: "操作人", dataIndex: "operator", width: 100, render: (value: string, row: SettlementContextRow) => financePersonDisplayName(value, row.operator_display_name) },
                  { title: "说明", dataIndex: "comment" },
                  {
                    title: "时间",
                    dataIndex: "created_at",
                    width: 170,
                    render: (value: string) =>
                      value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "—",
                  },
                ]
          }
        />
      )}
    </Modal>
  );
}
