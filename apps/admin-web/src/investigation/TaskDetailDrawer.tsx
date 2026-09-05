import { Drawer, Table, Card, Form, Alert, Input, Select, DatePicker, Cascader, Button, Space, Tag } from "antd";
import { isLegacyInvestigationRecord } from "./constants";
import type { Row, TaskRow, Contract, WarehouseCatalogItem } from "./types";

interface TaskDetailDrawerProps {
  open: boolean;
  taskTarget: Row | null;
  tasks: TaskRow[];
  creatingSubtask: boolean;
  taskForm: any;
  taskProvince: string | undefined;
  taskCity: string | undefined;
  contractOptions: Contract[];
  casePeopleOptions: { value: string; label: string; username?: string; search_text?: string }[];
  taskScopeGroups: { province: string; cities: string[] }[];
  taskCityOptions: string[];
  taskDistrictOptions: string[];
  taskAuthorizationScope: string;
  taskRegionOptions: any[];
  personDisplayName: (value: unknown) => string;
  onClose: () => void;
  onCreateTask: (nextAction: "complete" | "continue") => void;
}

export default function TaskDetailDrawer({
  open,
  taskTarget,
  tasks,
  creatingSubtask,
  taskForm,
  taskProvince,
  taskCity,
  contractOptions,
  casePeopleOptions,
  taskScopeGroups,
  taskCityOptions,
  taskDistrictOptions,
  taskAuthorizationScope,
  taskRegionOptions,
  personDisplayName,
  onClose,
  onCreateTask,
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
            render: (_value: unknown, row: TaskRow) =>
              row.data?.region || [row.data?.province, row.data?.city, row.data?.district].filter(Boolean).join(" ") || "—",
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
          <Form.Item name="authorization_scope" hidden>
            <Input />
          </Form.Item>
          {creatingSubtask && !tasks.some((task) => !task.parent_task_id) && (
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message={`父调查任务：${taskTarget?.serial_no || "当前调查任务"}`}
              description="本次子任务将自动继承当前调查任务的客户、合同、授权范围、授权时间和调查区域。"
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
            {!isLegacyInvestigationRecord(taskTarget) &&
              !taskTarget?.data.contract_id &&
              !taskTarget?.data.contract_record_id && (
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
            description={`授权时间：${taskTarget?.data.authorized_from || "未配置"} 至 ${taskTarget?.data.authorized_to || "未配置"}`}
          />
          <div className="form-grid">
            <Form.Item
              label="调查省份"
              name="province"
              rules={[{ required: true, message: "请选择授权范围内的调查省份" }]}
            >
              <Select
                placeholder="请选择授权范围内的省份"
                options={taskScopeGroups.map((group) => ({
                  value: group.province,
                  label: group.province,
                }))}
                onChange={() => taskForm.setFieldsValue({
                  city: undefined,
                  district: undefined,
                  region_path: [],
                })}
              />
            </Form.Item>
            <Form.Item
              label="调查城市"
              name="city"
              rules={[{ required: true, message: "请选择授权范围内的调查城市" }]}
            >
              <Select
                placeholder="请选择授权范围内的城市"
                disabled={!taskProvince}
                options={taskCityOptions.map((city) => ({ value: city, label: city }))}
                onChange={() => taskForm.setFieldsValue({ district: undefined, region_path: [] })}
              />
            </Form.Item>
            <Form.Item
              label="调查区/县"
              name="district"
              rules={[{ required: true, message: "请选择调查城市下的区/县" }]}
            >
              <Select
                placeholder="请选择调查城市下的区/县"
                disabled={!taskCity}
                options={taskDistrictOptions.map((district) => ({ value: district, label: district }))}
                onChange={(district) => {
                  if (taskProvince && taskCity) {
                    taskForm.setFieldValue("region_path", [taskProvince, taskCity, district]);
                  }
                }}
              />
            </Form.Item>
          </div>
          <Form.Item label="备注" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item
            label="调查区域"
            name="region_path"
            rules={[{ required: true, type: "array", min: 3, message: "请选择调查区域" }]}
            extra="按省、市、区/县选择调查区域，系统会自动继承到任务并限制在授权范围内"
          >
            <Cascader
              options={taskRegionOptions}
              placeholder="请选择调查区域"
              showSearch
              expandTrigger="hover"
              onChange={(path) => {
                const [provinceValue, cityValue, districtValue] = (path || []) as string[];
                taskForm.setFieldsValue({
                  province: provinceValue || "",
                  city: cityValue || "",
                  district: districtValue || "",
                });
              }}
            />
          </Form.Item>
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
