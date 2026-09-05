import { Alert,Button,Card,Checkbox,DatePicker,Descriptions,Form,Input,Modal,Select,Space,Table } from "antd";
import { personDisplayName } from "../constants";
import type { IprCaseEvent,IprDetailPageState,IprRecord,ReminderEventType } from "../types";

interface IprRemindersPanelProps {
  detail: IprRecord;
  iprSectionErrors: { reminders: string };
  iprCaseEvents: IprCaseEvent[];
  remindersPageState: IprDetailPageState;
  reminderEventTypes: ReminderEventType[];
  suppressedIds: number[];
  iprEventOpen: boolean;
  editingIprEvent: IprCaseEvent | null;
  iprEventDetail: IprCaseEvent | null;
  iprEventForm: any;
  suppressionOpen: boolean;
  profile: { role?: string; username?: string };
  onRefresh: () => void;
  onOpenEvent: (event?: IprCaseEvent) => void;
  onCloseEvent: () => void;
  onSaveEvent: () => void;
  onDeleteEvent: (row: IprCaseEvent) => Promise<void>;
  onSetEventDetail: (event: IprCaseEvent | null) => void;
  onOpenSuppression: () => void;
  onCloseSuppression: () => void;
  onSaveSuppressions: () => void;
  onSuppressedIdsChange: (ids: number[]) => void;
  canManageIprCaseEvent: (row: IprCaseEvent) => boolean;
  confirmIprDeletion: (kind: string, label: string, operation: () => Promise<void>) => void;
}

export function IprRemindersPanel({
  detail,
  iprSectionErrors,
  iprCaseEvents,
  remindersPageState,
  reminderEventTypes,
  suppressedIds,
  iprEventOpen,
  editingIprEvent,
  iprEventDetail,
  iprEventForm,
  suppressionOpen,
  profile,
  onRefresh,
  onOpenEvent,
  onCloseEvent,
  onSaveEvent,
  onDeleteEvent,
  onSetEventDetail,
  onOpenSuppression,
  onCloseSuppression,
  onSaveSuppressions,
  onSuppressedIdsChange,
  canManageIprCaseEvent,
  confirmIprDeletion,
}: IprRemindersPanelProps) {
  const remindersPagination = {
    current: remindersPageState.page,
    pageSize: remindersPageState.pageSize,
    total: remindersPageState.total,
    showSizeChanger: true,
    pageSizeOptions: ["15", "20", "50"],
    onChange: () => {},
  };

  return (
    <>
      <Card
        size="small"
        title="案件事件"
        style={{ marginTop: 16 }}
        extra={
          <Space>
            <Button size="small" onClick={onRefresh}>
              刷新
            </Button>
            {detail.status === "在办" && (
              <Button size="small" type="primary" onClick={() => onOpenEvent()}>
                新增事件
              </Button>
            )}
            {detail.status === "在办" && (
              <Button size="small" onClick={onOpenSuppression}>
                设定不监控
              </Button>
            )}
          </Space>
        }
      >
        {iprSectionErrors.reminders ? (
          <Alert
            type="error"
            showIcon
            message={iprSectionErrors.reminders}
            style={{ marginBottom: 12 }}
          />
        ) : null}
        <Table
          rowKey="id"
          size="small"
          pagination={remindersPagination}
          dataSource={iprCaseEvents}
          scroll={{ x: 790 }}
          columns={[
            { title: "事件类型", dataIndex: "event_type", width: 140 },
            { title: "事件日期", dataIndex: "event_date", width: 110 },
            { title: "截止日期", dataIndex: "deadline", width: 110 },
            {
              title: "事件内容",
              dataIndex: "content",
              ellipsis: true,
              render: (content: string, row: IprCaseEvent) => (
                <Button type="link" onClick={() => onSetEventDetail(row)}>
                  {content}
                </Button>
              ),
            },
            {
              title: "创建人",
              dataIndex: "creator_display_name",
              width: 100,
              render: personDisplayName,
            },
            {
              title: "操作",
              width: 130,
              render: (_, row: IprCaseEvent) =>
                detail.status === "在办" && canManageIprCaseEvent(row) ? (
                  <Space size={0}>
                    <Button type="link" onClick={() => onOpenEvent(row)}>
                      编辑
                    </Button>
                    <Button
                      type="link"
                      danger
                      onClick={() =>
                        confirmIprDeletion("event", row.content, () =>
                          onDeleteEvent(row)
                        )
                      }
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
        <div style={{ marginTop: 8, color: "#777" }}>
          不监控类型：
          {reminderEventTypes
            .filter((item) => suppressedIds.includes(item.id))
            .map((item) => item.name)
            .join("、") || "未设置"}
        </div>
      </Card>

      <Modal
        open={iprEventOpen}
        title={
          editingIprEvent
            ? "编辑知识产权案件事件"
            : "新增知识产权案件事件"
        }
        onCancel={onCloseEvent}
        onOk={onSaveEvent}
        okText={editingIprEvent ? "保存修改" : "创建事件"}
      >
        <Form form={iprEventForm} layout="vertical">
          <Form.Item
            name="event_type_id"
            label="事件类型"
            rules={[{ required: true }]}
          >
            <Select
              placeholder="选择事件类型"
              options={reminderEventTypes.map((item) => ({
                value: item.id,
                label: item.name,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="event_date"
            label="事件日期"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="deadline"
            label="截止日期"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="content"
            label="事件内容"
            rules={[{ required: true, message: "请输入事件内容" }]}
          >
            <Input.TextArea rows={3} maxLength={1000} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={!!iprEventDetail}
        title="案件事件详情"
        footer={null}
        onCancel={() => onSetEventDetail(null)}
      >
        {iprEventDetail && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="事件类型">
              {iprEventDetail.event_type}
            </Descriptions.Item>
            <Descriptions.Item label="事件日期">
              {iprEventDetail.event_date}
            </Descriptions.Item>
            <Descriptions.Item label="截止日期">
              {iprEventDetail.deadline}
            </Descriptions.Item>
            <Descriptions.Item label="创建人">
              {personDisplayName(iprEventDetail.creator_display_name)}
            </Descriptions.Item>
            <Descriptions.Item label="事件内容">
              {iprEventDetail.content}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
      <Modal
        open={suppressionOpen}
        title="案件提醒不监控"
        onCancel={onCloseSuppression}
        onOk={onSaveSuppressions}
        okText="保存设置"
      >
        <p style={{ color: "#777" }}>
          已勾选的类型不会参与后续自动提醒生成；手工新增提醒不受此设置影响。
        </p>
        <Checkbox.Group
          value={suppressedIds}
          onChange={(values) => onSuppressedIdsChange(values.map(Number))}
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2,minmax(0,1fr))",
            gap: 8,
          }}
          options={reminderEventTypes.map((item) => ({
            label: item.name,
            value: item.id,
          }))}
        />
      </Modal>
    </>
  );
}
