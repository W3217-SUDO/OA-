import { Drawer, Card, Form, Alert, Input, Select, DatePicker, Cascader, Button, Space, Tag } from "antd";
import Table from "../components/ResizableTable";
import { isLegacyInvestigationRecord } from "./constants";
import { taskRegionLabel } from "./taskRegionDisplay";
import type { Row, TaskRow, Contract } from "./types";

interface TaskDetailDrawerProps {
  open: boolean;
  taskTarget: Row | null;
  authorizationTarget: Row | null;
  tasks: TaskRow[];
  creatingSubtask: boolean;
  taskForm: any;
  contractOptions: Contract[];
  casePeopleOptions: { value: string; label: string; username?: string; search_text?: string }[];
  taskAuthorizationScope: string;
  taskRegionOptions: any[];
  personDisplayName: (value: unknown) => string;
  onClose: () => void;
  onCreateTask: (nextAction: "complete" | "continue") => void;
  onParentTaskChange: (parentId: number) => void;
}

export default function TaskDetailDrawer({
  open,
  taskTarget,
  authorizationTarget,
  tasks,
  creatingSubtask,
  taskForm,
  contractOptions,
  casePeopleOptions,
  taskAuthorizationScope,
  taskRegionOptions,
  personDisplayName,
  onClose,
  onCreateTask,
  onParentTaskChange,
}: TaskDetailDrawerProps) {
  return (
    <Drawer
      size={760}
      open={open}
      title={`调查任务：${taskTarget?.serial_no || ""}`}
      onClose={onClose}
    >
      <Table
        rowKey="id"
        size="small"
        pagination={false}
        scroll={{ x: 840 }}
        dataSource={tasks}
        columns={[
          { title: "任务编号", dataIndex: "serial_no", width: 165 },
          {
            title: "任务名称",
            dataIndex: "title",
            width: 220,
            ellipsis: { showTitle: true },
          },
          {
            title: "父调查任务",
            dataIndex: "parent_task_no",
            width: 150,
            render: (v: string, row: TaskRow) =>
              v || row.investigation_no || taskTarget?.serial_no || "—",
          },
          {
            title: "调查员",
            dataIndex: "owner",
            width: 90,
            render: (_value: unknown, row: TaskRow) =>
              row.owner_display_name || personDisplayName(row.owner),
          },
          {
            title: "调查区域",
            width: 160,
            ellipsis: { showTitle: true },
            render: (_value: unknown, row: TaskRow) =>
              taskRegionLabel(row.data),
          },
          {
            title: "开始时间",
            width: 110,
            render: (_value: unknown, row: TaskRow) => row.data?.start_date || row.data?.authorized_from || "—",
          },
          {
            title: "结束时间",
            width: 110,
            render: (_value: unknown, row: TaskRow) => row.data?.end_date || row.deadline || row.data?.authorized_to || "—",
          },
          {
            title: "状态",
            dataIndex: "status",
            width: 90,
            render: (v: string) => <Tag>{v}</Tag>,
          },
        ]}
      />
      <Card
        size="small"
        title={
          creatingSubtask
            ? "新增子任务"
            : tasks.length
              ? "新增主任务/子任务"
              : "创建首个调查任务"
        }
        style={{ marginTop: 16 }}
      >
        <Form form={taskForm} layout="vertical">
          {creatingSubtask && !tasks.some((task) => !task.parent_task_id) && (
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message={`父调查任务：${taskTarget?.serial_no || "当前调查任务"}`}
              description="本次子任务使用父调查事项的客户、合同及当前授权范围，请在授权范围内选择调查区域。"
            />
          )}
          <Form.Item
            label="任务名称"
            name="title"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          {creatingSubtask && tasks.some((task) => !task.parent_task_id) && (
            <Form.Item
              label="父调查任务"
              name="parent_task_id"
              rules={[{ required: true, message: "请选择父任务" }]}
            >
              <Select
                onChange={onParentTaskChange}
                options={tasks
                  .filter((task) => !task.parent_task_id)
                  .map((task) => ({
                    value: task.id,
                    label: `${task.serial_no}｜${task.title}`,
                  }))}
              />
            </Form.Item>
          )}
          <div className="form-grid">
            {!isLegacyInvestigationRecord(authorizationTarget) &&
              !authorizationTarget?.data.contract_id &&
              !authorizationTarget?.data.contract_record_id && (
                <Form.Item
                  label="关联合同"
                  name="contract_record_id"
                  rules={[{ required: true, message: "请绑定与调查客户一致的合同" }]}
                >
                  <Select
                    showSearch
                    optionFilterProp="label"
                    placeholder="选择后将固定绑定到调查任务"
                    options={contractOptions.map((contract) => ({
                      value: contract.id,
                      label: `${contract.serial_no}｜${contract.title}`,
                    }))}
                  />
                </Form.Item>
              )}
            <Form.Item
              label="调查员"
              name="owner"
              rules={[{ required: true }]}
            >
              <Select
                showSearch
                filterOption={(input, option) =>
                  String(option?.search_text || option?.label || "").toLocaleLowerCase().includes(input.toLocaleLowerCase())
                }
                placeholder="请选择系统人员"
                options={casePeopleOptions.map((item) => ({
                  value: item.username || item.value,
                  label: item.label || item.value,
                  search_text: item.search_text || `${item.label || item.value} ${item.username || item.value}`,
                }))}
              />
            </Form.Item>
            <Form.Item
              label="开始日期"
              name="start_date"
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="结束日期"
              name="end_date"
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="截止日期"
              name="deadline"
              rules={[{ required: true }]}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="优先级" name="priority">
              <Select
                options={["普通", "紧急", "特急"].map((v) => ({
                  value: v,
                  label: v,
                }))}
              />
            </Form.Item>
          </div>
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message={`授权区域：${taskAuthorizationScope || "未配置"}`}
            description={`授权时间：${authorizationTarget?.data.authorized_from || "未配置"} 至 ${authorizationTarget?.data.authorized_to || "未配置"}`}
          />
          <Form.Item label="备注" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item
            label="调查区域"
            name="investigation_regions"
            rules={[{ required: true, type: "array", min: 1, message: "请至少选择一个调查区域" }]}
            extra="可跨省选择多个省、市，调查区域须在父任务授权范围内"
          >
            <Cascader
              options={taskRegionOptions}
              multiple
              changeOnSelect
              maxTagCount={3}
              placeholder="请选择一个或多个调查区域"
              showSearch
              expandTrigger="hover"
            />
          </Form.Item>
          <Space style={{ marginBottom: 16 }}>
            <Button size="small" onClick={() => taskForm.setFieldValue(
              "investigation_regions",
              taskRegionOptions.flatMap((province) =>
                province.children.map((city: { value: string }) => [province.value, city.value]),
              ),
            )}>全选授权区域</Button>
            <Button size="small" onClick={() => taskForm.setFieldValue("investigation_regions", [])}>清空</Button>
          </Space>
          <Space>
            <Button type="primary" onClick={() => onCreateTask("complete")}>
              完成
            </Button>
            <Button onClick={() => onCreateTask("continue")}>
              继续分配
            </Button>
          </Space>
        </Form>
      </Card>
    </Drawer>
  );
}
