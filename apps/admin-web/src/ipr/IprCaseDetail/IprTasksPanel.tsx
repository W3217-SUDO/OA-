import { Alert,Button,Card,DatePicker,Form,Input,Modal,Select,Space,Table,Tag } from "antd";
import { personDisplayName } from "../constants";
import type { IprCaseTask,IprDetailPageState,IprRecord,PeopleOption } from "../types";

interface IprTasksPanelProps {
  detail: IprRecord;
  iprSectionErrors: { tasks: string };
  iprCaseTasks: IprCaseTask[];
  iprTasksPageState: IprDetailPageState;
  iprTaskOpen: boolean;
  iprTaskForm: any;
  peopleOptions: PeopleOption[];
  onRefresh: () => void;
  onOpenTask: (record: IprRecord) => void;
  onCloseTask: () => void;
  onCreateTask: () => void;
}

export function IprTasksPanel({
  detail,
  iprSectionErrors,
  iprCaseTasks,
  iprTasksPageState,
  iprTaskOpen,
  iprTaskForm,
  peopleOptions,
  onRefresh,
  onOpenTask,
  onCloseTask,
  onCreateTask,
}: IprTasksPanelProps) {
  const iprTasksPagination = {
    current: iprTasksPageState.page,
    pageSize: iprTasksPageState.pageSize,
    total: iprTasksPageState.total,
    showSizeChanger: true,
    pageSizeOptions: ["15", "20", "50"],
    onChange: () => {},
  };

  return (
    <>
      <Card
        size="small"
        title="关联任务"
        style={{ marginTop: 16 }}
        extra={
          <Space>
            <Button size="small" onClick={onRefresh}>
              刷新
            </Button>
            {detail.status === "在办" && (
              <Button
                size="small"
                type="primary"
                onClick={() => onOpenTask(detail)}
              >
                新建案件任务
              </Button>
            )}
          </Space>
        }
      >
        {iprSectionErrors.tasks ? (
          <Alert
            type="error"
            showIcon
            message={iprSectionErrors.tasks}
            style={{ marginBottom: 12 }}
          />
        ) : null}
        <Table
          rowKey="id"
          size="small"
          pagination={iprTasksPagination}
          dataSource={iprCaseTasks}
          scroll={{ x: 760 }}
          columns={[
            {
              title: "任务编号",
              dataIndex: "serial_no",
              width: 170,
              ellipsis: true,
            },
            { title: "标题", dataIndex: "title", ellipsis: true },
            {
              title: "负责人",
              dataIndex: "owner_display_name",
              width: 110,
              render: personDisplayName,
            },
            {
              title: "截止日期",
              dataIndex: "deadline",
              width: 110,
              render: (value) => value || "—",
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 105,
              render: (value) => <Tag>{value}</Tag>,
            },
          ]}
        />
      </Card>

      <Modal
        open={iprTaskOpen}
        title={detail ? `新建案件任务：${detail.serial_no}` : "新建案件任务"}
        onCancel={onCloseTask}
        onOk={onCreateTask}
        okText="创建任务"
      >
        <Form form={iprTaskForm} layout="vertical">
          <Form.Item
            name="title"
            label="任务标题"
            rules={[{ required: true, message: "请输入任务标题" }]}
          >
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item
            name="owner"
            label="负责人"
            rules={[{ required: true, message: "请选择负责人" }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="请选择系统员工"
              options={peopleOptions.map((item) => ({
                value: item.username,
                label: item.label,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="deadline"
            label="截止日期"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="priority" label="优先级">
            <Select
              options={["普通", "重要", "紧急"].map((value) => ({
                value,
                label: value,
              }))}
            />
          </Form.Item>
          <Form.Item name="description" label="任务说明">
            <Input.TextArea rows={3} maxLength={2000} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
