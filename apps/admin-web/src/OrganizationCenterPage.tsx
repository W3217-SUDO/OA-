import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Empty,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tree,
} from "antd";
import type { TableColumnsType, TreeDataNode } from "antd";
import { DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import { api } from "./api";
import "./organization-center.css";

type Department = {
  id: number;
  code: string;
  name: string;
  manager: string;
  permissions: string[];
  permission_source_department_id?: number | null;
  sort_order: number;
  is_active: boolean;
};
type JobRole = {
  id: number;
  code: string;
  name: string;
  permissions: string[];
  description: string;
  sort_order: number;
  is_active: boolean;
};
const permissionGroups = [
  {
    name: "客户管理",
    items: [
      "客户查看",
      "客户新建",
      "客户修改",
      "客户分配",
      "客户回收/恢复",
      "客户共享",
      "利益冲突检索",
    ],
  },
  {
    name: "合同中心",
    items: [
      "合同查看",
      "合同新建",
      "合同修改",
      "合同提交审批",
      "合同审批",
      "合同归档",
    ],
  },
  {
    name: "案件中心",
    items: [
      "案件查看",
      "案件新建",
      "案件分配",
      "案件承办",
      "案件进展维护",
      "开庭排期",
      "案件办结",
      "案件归档申请",
      "案件归档审核",
    ],
  },
  {
    name: "调查大厅",
    items: [
      "调查任务发起",
      "调查任务办理",
      "线索审核",
      "公证管理",
      "证据管理",
    ],
  },
  {
    name: "事务中心",
    items: [
      "任务查看",
      "任务派发",
      "任务接受",
      "任务协作",
      "任务交接",
      "任务完成确认",
    ],
  },
  {
    name: "收发文台",
    items: [
      "收文登记",
      "发文登记",
      "文书模板维护",
      "业务附件上传/下载",
      "智能文档生成",
      "智能文档人工确认",
    ],
  },
  {
    name: "用印中心",
    items: [
      "用印申请",
      "用印审批",
      "印章管理",
    ],
  },
  {
    name: "财务中心 / 平台财务中心",
    items: [
      "费用查看",
      "费用申请",
      "费用审批",
      "回款登记",
      "回款分配",
      "付款登记",
      "付款审批",
      "开票申请",
      "开票审批",
      "退款办理",
      "内部结算",
      "对账",
    ],
  },
  {
    name: "人事中心",
    items: [
      "员工查看",
      "员工新建",
      "员工修改",
      "部门管理",
      "岗位角色管理",
    ],
  },
  {
    name: "仓库管理",
    items: [
      "仓库查看",
      "仓库出入库",
    ],
  },
  {
    name: "报表中心",
    items: [
      "报表查看",
      "报表导出",
    ],
  },
  {
    name: "系统中心",
    items: [
      "系统用户管理",
      "系统权限配置",
      "系统参数配置",
      "审计日志查看",
    ],
  },
];
const permissionTreeData: TreeDataNode[] = permissionGroups.map((group) => ({
  key: `group:${group.name}`,
  title: group.name,
  children: group.items.map((item) => ({ key: item, title: item })),
}));

export default function OrganizationCenterPage({
  initialView = "hr-departments",
}: {
  initialView?: string;
}) {
  const rolesView = initialView === "hr-roles";
  const [departments, setDepartments] = useState<Department[]>([]),
    [roles, setRoles] = useState<JobRole[]>([]),
    [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false),
    [editingDepartment, setEditingDepartment] = useState<Department | null>(
      null,
    ),
    [editingRole, setEditingRole] = useState<JobRole | null>(null),
    [permissionRole, setPermissionRole] = useState<JobRole | null>(null),
    [selectedRolePermissions, setSelectedRolePermissions] = useState<string[]>([]);
  const [departmentForm] = Form.useForm(),
    [roleForm] = Form.useForm();
  const load = async () => {
    setLoading(true);
    try {
      const [departmentResult, roleResult] = await Promise.all([
        api.get("/hr/departments"),
        api.get("/hr/job-roles"),
      ]);
      setDepartments(departmentResult.data.items);
      setRoles(roleResult.data.items);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "组织数据加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const start = (row?: Department | JobRole) => {
    if (rolesView) {
      const role = row as JobRole | undefined;
      setEditingRole(role || null);
      setEditingDepartment(null);
      roleForm.resetFields();
      roleForm.setFieldsValue(
        role || {
          permissions: [],
          sort_order: roles.length + 1,
          is_active: true,
        },
      );
    } else {
      const department = row as Department | undefined;
      setEditingDepartment(department || null);
      setEditingRole(null);
      departmentForm.resetFields();
      departmentForm.setFieldsValue(
        department || {
          permissions: [],
          permission_source_department_id: null,
          sort_order: departments.length + 1,
          is_active: true,
        },
      );
    }
    setOpen(true);
  };
  const copyDepartmentPermissions = (sourceId: number | undefined) => {
    if (!sourceId) return;
    const source = departments.find((item) => item.id === sourceId);
    departmentForm.setFieldValue("permissions", source?.permissions || []);
  };
  const save = async () => {
    try {
      if (rolesView) {
        const value = await roleForm.validateFields();
        if (editingRole)
          await api.patch(`/hr/job-roles/${editingRole.id}`, value);
        else await api.post("/hr/job-roles", value);
      } else {
        const value = await departmentForm.validateFields();
        value.permission_source_department_id ??= null;
        if (editingDepartment)
          await api.patch(`/hr/departments/${editingDepartment.id}`, value);
        else await api.post("/hr/departments", value);
      }
      message.success("保存成功");
      setOpen(false);
      void load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "保存失败");
    }
  };
  const removeDepartment = async (row: Department) => {
    try {
      await api.delete(`/hr/departments/${row.id}`);
      message.success("删除成功");
      void load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const removeRole = async (row: JobRole) => {
    try {
      await api.delete(`/hr/job-roles/${row.id}`);
      message.success("删除成功");
      void load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const openRolePermissions = (row: JobRole) => {
    setPermissionRole(row);
    setSelectedRolePermissions(row.permissions || []);
  };
  const saveRolePermissions = async () => {
    if (!permissionRole) return;
    try {
      await api.patch(`/hr/job-roles/${permissionRole.id}`, {
        permissions: selectedRolePermissions,
      });
      message.success("角色权限已保存");
      setPermissionRole(null);
      void load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "角色权限保存失败");
    }
  };
  const departmentColumns: TableColumnsType<Department> = [
    { title: "序号", key: "no", width: 70, render: (_v, _r, i) => i + 1 },
    { title: "部门名称", dataIndex: "name", width: 180 },
    { title: "部门代码", dataIndex: "code", width: 150 },
    {
      title: "部门负责人",
      dataIndex: "manager",
      width: 130,
      render: (value) => value || "—",
    },
    {
      title: "业务权限",
      dataIndex: "permissions",
      width: 100,
      render: (values: string[]) => `${values?.length || 0} 项`,
    },
    {
      title: "权限来源",
      key: "permission_source",
      width: 180,
      render: (_v, row) =>
        row.permission_source_department_id
          ? departments.find(
              (item) => item.id === row.permission_source_department_id,
            )?.name || "已删除来源"
          : "手动配置",
    },
    { title: "排序", dataIndex: "sort_order", width: 75 },
    {
      title: "可用",
      dataIndex: "is_active",
      width: 75,
      render: (value) => (value ? "是" : "否"),
    },
    {
      title: "操作",
      key: "action",
      width: 130,
      fixed: "right",
      render: (_v, row) => (
        <Space size={0}>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => start(row)}
          >
            修改
          </Button>
          <Popconfirm
            title="确认删除该部门？"
            onConfirm={() => removeDepartment(row)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];
  const roleColumns: TableColumnsType<JobRole> = [
    { title: "序号", key: "no", width: 70, render: (_v, _r, i) => i + 1 },
    { title: "角色名称", dataIndex: "name", width: 240 },
    {
      title: "角色权限",
      key: "permissions",
      render: (_v, row) => <Button type="link" onClick={() => openRolePermissions(row)}>权限设定</Button>,
    },
    {
      title: "操作",
      key: "action",
      width: 170,
      render: (_v, row) => (
        <Space size={0}>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => start(row)}
          >
            修改
          </Button>
          <Popconfirm
            title="确认删除该角色？"
            onConfirm={() => removeRole(row)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];
  const title = rolesView ? "角色列表" : "部门列表",
    button = rolesView ? "新增角色" : "新增部门";
  const emptyContent = (
    <div className="organization-empty">
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
      {rolesView && (
        <Button type="primary" icon={<PlusOutlined />} onClick={() => start()}>
          新增角色
        </Button>
      )}
    </div>
  );
  return (
    <>
      <Card className="panel organization-panel" title={title}>
        <div className="organization-action">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => start()}
          >
            {button}
          </Button>
        </div>
        {rolesView ? (
          <Table
            rowKey="id"
            size="small"
            loading={loading}
            columns={roleColumns}
            dataSource={roles}
            locale={{ emptyText: emptyContent }}
            pagination={{
              pageSize: 20,
              showTotal: (total) => `共 ${total} 条`,
            }}
          />
        ) : (
          <Table
            rowKey="id"
            size="small"
            loading={loading}
            columns={departmentColumns}
            dataSource={departments}
            scroll={{ x: 1080 }}
            locale={{ emptyText: emptyContent }}
            pagination={{
              pageSize: 20,
              showTotal: (total) => `共 ${total} 条`,
            }}
          />
        )}
      </Card>
      <Modal
        open={open}
        title={`${editingDepartment || editingRole ? "修改" : "新增"}${rolesView ? "角色" : "部门"}`}
        okText="保存"
        cancelText="取消"
        onOk={save}
        onCancel={() => setOpen(false)}
        destroyOnHidden
        width={rolesView ? 560 : 980}
      >
        {rolesView ? (
          <Form form={roleForm} layout="vertical">
            <div className="organization-form-grid">
              <Form.Item
                label="角色名称"
                name="name"
                rules={[{ required: true }]}
              >
                <Input disabled={editingRole?.code === "SYSTEM-ADMIN"} />
              </Form.Item>
              <Form.Item
                label="角色代码"
                name="code"
                rules={[{ required: true }]}
              >
                <Input disabled={editingRole?.code === "SYSTEM-ADMIN"} />
              </Form.Item>
              <Form.Item
                label="排序号"
                name="sort_order"
                rules={[{ required: true }]}
              >
                <InputNumber min={0} style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item
                label="是否可用"
                name="is_active"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
              <Form.Item className="span-2" label="说明" name="description">
                <Input.TextArea rows={2} />
              </Form.Item>
            </div>
          </Form>
        ) : (
          <Form form={departmentForm} layout="vertical">
            <div className="organization-form-grid">
              <Form.Item className="span-2">
                <Alert
                  type="info"
                  showIcon
                  title="部门可复用已有部门的业务动作权限"
                  description="选择权限来源部门后会复制该部门当前权限；后续可单独调整。菜单、数据范围和敏感字段仍由系统角色统一控制。"
                />
              </Form.Item>
              <Form.Item
                label="部门名称"
                name="name"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                label="部门代码"
                name="code"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                className="span-2"
                label="权限来源部门（可选）"
                name="permission_source_department_id"
              >
                <Select
                  allowClear
                  placeholder="手动配置权限，或选择一个已有部门复制权限"
                  options={departments
                    .filter((item) => item.id !== editingDepartment?.id)
                    .map((item) => ({
                      value: item.id,
                      label: `${item.name}（${item.permissions?.length || 0} 项）`,
                    }))}
                  onChange={copyDepartmentPermissions}
                />
              </Form.Item>
              <Form.Item
                className="span-2"
                label="业务动作权限"
                name="permissions"
              >
                <Checkbox.Group className="job-permission-matrix">
                  {permissionGroups.map((group) => (
                    <section key={group.name}>
                      <b>{group.name}</b>
                      <div>
                        {group.items.map((item) => (
                          <Checkbox key={item} value={item}>
                            {item}
                          </Checkbox>
                        ))}
                      </div>
                    </section>
                  ))}
                </Checkbox.Group>
              </Form.Item>
              <Form.Item label="部门负责人" name="manager">
                <Input />
              </Form.Item>
              <Form.Item
                label="排序号"
                name="sort_order"
                rules={[{ required: true }]}
              >
                <InputNumber min={0} style={{ width: "100%" }} />
              </Form.Item>
              <Form.Item
                label="是否可用"
                name="is_active"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </div>
          </Form>
        )}
      </Modal>
      <Modal
        open={Boolean(permissionRole)}
        title="角色维护"
        okText="确定"
        cancelText="取消"
        onOk={() => void saveRolePermissions()}
        onCancel={() => setPermissionRole(null)}
        destroyOnHidden
        width={560}
      >
        <Form layout="horizontal" labelCol={{ span: 7 }} wrapperCol={{ span: 15 }}>
          <Form.Item label="角色名称">
            <Input value={permissionRole?.name || ""} readOnly />
          </Form.Item>
          <Form.Item label="菜单及动作权限">
            <div className="legacy-role-permission-tree">
              <Tree
                checkable
                defaultExpandAll
                treeData={permissionTreeData}
                checkedKeys={selectedRolePermissions}
                disabled={permissionRole?.code === "SYSTEM-ADMIN"}
                onCheck={(checked) => setSelectedRolePermissions((Array.isArray(checked) ? checked : checked.checked).filter((key): key is string => typeof key === "string" && !key.startsWith("group:")))}
              />
            </div>
          </Form.Item>
          {permissionRole?.code === "SYSTEM-ADMIN" && <Form.Item wrapperCol={{ offset: 7, span: 15 }}><Alert type="info" showIcon title="系统管理员权限由系统强制保持完整，不能在此降权。" /></Form.Item>}
        </Form>
      </Modal>
    </>
  );
}
