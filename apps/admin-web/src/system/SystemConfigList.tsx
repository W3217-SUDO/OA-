import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Empty,
  Form,
  InputNumber,
  message,
  Modal,
  Select,
  Space,
  Switch,
  Tag,
} from "antd";
import Table from "../components/ResizableTable";
import { api } from "../api";
import type { SystemConfig } from "./types";

interface SystemConfigListProps {
  configs: SystemConfig[];
}

export function SystemConfigList({ configs }: SystemConfigListProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [autoReviewSaving, setAutoReviewSaving] = useState(false);
  const [autoReviewOverride, setAutoReviewOverride] = useState<SystemConfig | null>(null);
  const [staffOverride, setStaffOverride] = useState<SystemConfig | null>(null);
  const [staffVisible, setStaffVisible] = useState(false);
  const [staffSaving, setStaffSaving] = useState(false);
  const [userOptions, setUserOptions] = useState<{ label: string; value: string }[]>([]);
  const [staffForm] = Form.useForm();
  const empty = (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
  );

  useEffect(() => {
    setAutoReviewOverride(null);
    setStaffOverride(null);
  }, [configs]);

  const saveAutoReview = async (enabled: boolean) => {
    setAutoReviewSaving(true);
    try {
      const { data } = await api.patch<SystemConfig>("/system/configs/conflict_auto_review", { value: { enabled } });
      if (data.value?.enabled !== enabled) throw new Error("服务器返回的自动利冲审查配置不一致");
      setAutoReviewOverride(data);
      message.success("配置已保存");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || error?.message || "自动利冲审查配置保存失败");
    } finally {
      setAutoReviewSaving(false);
    }
  };

  const openStaff = async (row: SystemConfig) => {
    const current = staffOverride || row;
    const companies = current.value?.companies || {};
    staffForm.setFieldsValue({
      companies: Object.entries(companies).map(([companyId, staff]: [string, any]) => ({
        companyId: Number(companyId),
        notaryHandover: staff.notary_handover_username || undefined,
        warehouse: staff.warehouse_username || undefined,
      })),
    });
    try {
      const { data } = await api.get("/system/configs");
      setUserOptions((data.investigation_supervisor_options || []).map(
        (user: { username: string; display_name: string }) => ({
          value: user.username, label: `${user.display_name}（${user.username}）`,
        }),
      ));
      setStaffVisible(true);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "人员列表加载失败");
    }
  };

  const saveStaff = async () => {
    const values = await staffForm.validateFields();
    const companies: Record<string, { notary_handover_username: string; warehouse_username: string }> = {};
    for (const row of values.companies || []) {
      const key = String(row.companyId);
      if (companies[key]) {
        message.error("同一公司只能配置一组交接人员");
        return;
      }
      companies[key] = {
        notary_handover_username: row.notaryHandover || "",
        warehouse_username: row.warehouse || "",
      };
    }
    setStaffSaving(true);
    try {
      const { data } = await api.patch<SystemConfig>("/system/configs/automatic_task_staff", { value: { companies } });
      setStaffOverride(data);
      setStaffVisible(false);
      message.success("案件自动任务人员配置已保存");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "人员配置保存失败");
    } finally {
      setStaffSaving(false);
    }
  };

  return (
    <>
      <Card className="panel system-focused" title="系统配置">
        <Table<SystemConfig>
          rowKey="key"
          size="small"
          columns={[
            {
              title: "序号",
              key: "no",
              width: 70,
              render: (_v: unknown, _r: unknown, i: number) => i + 1,
            },
            { title: "配置项组", dataIndex: "group", width: 150 },
            { title: "配置项名称", dataIndex: "label", width: 180 },
            { title: "配置项主键", dataIndex: "key", width: 190 },
            {
              title: "键值",
              dataIndex: "value",
              render: (value: Record<string, any>, row: SystemConfig) => {
                if (row.key === "automatic_task_staff") {
                  const current = staffOverride || row;
                  const count = Object.keys(current.value?.companies || {}).length;
                  return (
                    <Space>
                      <span>已配置 {count} 家公司</span>
                      <Button size="small" onClick={() => void openStaff(row)}>配置人员</Button>
                    </Space>
                  );
                }
                if (row.key !== "conflict_auto_review") return JSON.stringify(value);
                const current = autoReviewOverride || row;
                const enabled = current.value?.enabled === true;
                const statusAvailable = typeof current.ready === "boolean" && typeof current.effective === "boolean";
                return (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <Switch
                      aria-label="自动利冲审查总开关"
                      checked={enabled}
                      loading={autoReviewSaving}
                      disabled={autoReviewSaving || (!enabled && current.ready !== true)}
                      onChange={(checked) => void saveAutoReview(checked)}
                    />
                    <Tag color={current.effective ? "green" : "default"}>
                      {current.effective ? "自动审查运行中" : "自动审查未运行"}
                    </Tag>
                    <span style={{ color: statusAvailable ? "#666" : "#cf1322" }}>
                      {statusAvailable ? current.reason || (enabled ? "已开启" : "已关闭") : "自动利冲审查状态不可用"}
                    </span>
                  </div>
                );
              },
            },
          ]}
          dataSource={configs}
          locale={{ emptyText: empty }}
          pagination={{
            current: page,
            pageSize,
            showSizeChanger: true,
            pageSizeOptions: ["10", "15", "20", "50", "100", "200"],
            showQuickJumper: true,
            showTotal: (total) => `共有${total}条`,
            onChange: (nextPage, nextPageSize) => {
              setPage(nextPage);
              setPageSize(nextPageSize);
            },
          }}
        />
      </Card>
      <Modal
        title="案件自动任务交接人员"
        open={staffVisible}
        onCancel={() => setStaffVisible(false)}
        onOk={() => void saveStaff()}
        okButtonProps={{ loading: staffSaving }}
        width={800}
      >
        <Form form={staffForm} layout="vertical" initialValues={{ companies: [] }}>
          <Form.List name="companies">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space key={field.key} align="start" wrap>
                    <Form.Item name={[field.name, "companyId"]} label="公司编号" rules={[{ required: true, message: "填写公司编号" }]}>
                      <InputNumber min={1} precision={0} />
                    </Form.Item>
                    <Form.Item name={[field.name, "notaryHandover"]} label="公证书交接人员">
                      <Select options={userOptions} showSearch optionFilterProp="label" allowClear style={{ width: 240 }} />
                    </Form.Item>
                    <Form.Item name={[field.name, "warehouse"]} label="证物仓库管理员">
                      <Select options={userOptions} showSearch optionFilterProp="label" allowClear style={{ width: 240 }} />
                    </Form.Item>
                    <Button danger onClick={() => remove(field.name)}>删除</Button>
                  </Space>
                ))}
                <Button onClick={() => add()}>新增公司配置</Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </>
  );
}
