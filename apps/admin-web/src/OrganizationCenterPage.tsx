import { POPUP_WIDTH } from "./components/common/popupSize";
import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
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
  Tag,
  Tooltip,
  Tree,
} from "antd";
import Table from "./components/ResizableTable";
import type { TableColumnsType, TreeDataNode } from "antd";
import { DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import { api } from "./api";
import { notifyPermissionsUpdated } from "./workspacePermissions";
// @ts-ignore Role-gated organization actions are covered by a standalone Node test.
import { canDeleteOrganizationRole, organizationActionAccess } from "./hrAccessGuard.mjs";
import "./organization-center.css";

type Department = {
  id: number;
  code: string;
  name: string;
  parent_department_id: number | null;
  parent_department_name: string;
  manager: string;
  manager_display_name?: string;
  manager_display_name_missing?: boolean;
  owner_username?: string;
  owner_display_name?: string;
  owner_display_name_missing?: boolean;
  overdue_deduction: boolean;
  sort_order: number;
  is_active: boolean;
  created_by?: string;
  created_by_display_name?: string;
  created_by_display_name_missing?: boolean;
  updated_by?: string;
  updated_by_display_name?: string;
  updated_by_display_name_missing?: boolean;
  created_at?: string;
  updated_at?: string;
};
type PeopleOption = { value: string; label: string; username: string; search_text?: string };
type JobRole = {
  id: number;
  code: string;
  name: string;
  permissions: string[];
  field_keys: string[];
  field_keys_configured: boolean;
  data_scope: string | null;
  description: string;
  sort_order: number;
  is_active: boolean;
  created_by?: string;
  created_by_display_name?: string;
  created_by_display_name_missing?: boolean;
  updated_by?: string;
  updated_by_display_name?: string;
  updated_by_display_name_missing?: boolean;
  created_at?: string;
  updated_at?: string;
};
const PERSON_NAME_PLACEHOLDER = "【待补充中文姓名】";
const renderPersonReference = (displayName?: string, missing?: boolean) => {
  const name = displayName || PERSON_NAME_PLACEHOLDER;
  if (!missing) return name;
  return (
    <Tooltip title="请到人事中心员工管理补充中文姓名">
      <Tag color="orange">{name}</Tag>
    </Tooltip>
  );
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
      "利益冲突审批",
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
      "案件法院信息修改",
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
    name: "任务中心",
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
const rolePermissionTreeMenuCodes = (
  nodes: TreeDataNode[] = [],
  menuCodes = new Set<string>(),
) => {
  nodes.forEach((node) => {
    const key = String(node.key);
    if (key.startsWith("menu:")) menuCodes.add(key.slice("menu:".length));
    if (Array.isArray(node.children)) {
      rolePermissionTreeMenuCodes(node.children as TreeDataNode[], menuCodes);
    }
  });
  return menuCodes;
};
// 同一开关挂在多个页面下时，其他页面下的节点 key 为“action:功能码#页面”，勾选、保存都按同一个功能码。
const roleActionBaseKey = (key: string) => (key.startsWith("action:") ? key.split("#")[0] : key);
const rolePermissionTreeActionKeys = (nodes: TreeDataNode[] = [], keys: string[] = []) => {
  nodes.forEach((node) => {
    const key = String(node.key);
    if (key.startsWith("action:")) keys.push(roleActionBaseKey(key));
    if (Array.isArray(node.children)) rolePermissionTreeActionKeys(node.children as TreeDataNode[], keys);
  });
  return keys;
};
const rolePermissionMenuBranch = (nodes: TreeDataNode[], target: string): string[] => {
  for (const node of nodes) {
    if (String(node.key) === target) {
      // 勾选页面时连同它下面的具体功能一起勾上，管理员再按角色取消不需要的功能。
      return [
        ...Array.from(rolePermissionTreeMenuCodes([node])).map((code) => `menu:${code}`),
        ...rolePermissionTreeActionKeys([node]),
      ];
    }
    const branch = rolePermissionMenuBranch((node.children || []) as TreeDataNode[], target);
    if (branch.length) return branch;
  }
  return [];
};
// 区块下功能全勾时区块显示为勾上（区块本身不保存）。
const rolePermissionCheckedGroups = (nodes: TreeDataNode[], selected: string[]): string[] => {
  const checked = new Set(selected);
  const visit = (items: TreeDataNode[]) => items.forEach((node) => {
    const children = (node.children || []) as TreeDataNode[];
    if (String(node.key).startsWith("group:")) {
      const actions = rolePermissionTreeActionKeys(children);
      if (actions.length && actions.every((key) => checked.has(key))) checked.add(String(node.key));
    }
    if (String(node.key).includes("#") && checked.has(roleActionBaseKey(String(node.key)))) checked.add(String(node.key));
    visit(children);
  });
  visit(nodes);
  return Array.from(checked);
};
const normalizeRolePermissionCheckedKeys = (keys: readonly unknown[]) =>
  keys.filter(
    (key): key is string =>
      typeof key === "string" && !key.startsWith("group:") && key !== "actions",
  );
const rolePermissionsToTreeCheckedKeys = (
  permissions: string[] = [],
  treeData: TreeDataNode[] = permissionTreeData,
) => {
  const menuCodes = rolePermissionTreeMenuCodes(treeData);
  return permissions.map((key) => (menuCodes.has(key) ? `menu:${key}` : key));
};
const rolePermissionTreeKeysToPayload = (keys: readonly string[]) =>
  Array.from(
    new Set(
      normalizeRolePermissionCheckedKeys(keys).map((key) =>
        key.startsWith("menu:") ? key.slice("menu:".length) : key,
      ),
    ),
  );

export default function OrganizationCenterPage({
  initialView = "hr-departments",
}: {
  initialView?: string;
}) {
  const rolesView = initialView === "hr-roles";
  const [departments, setDepartments] = useState<Department[]>([]),
    [roles, setRoles] = useState<JobRole[]>([]),
    [loading, setLoading] = useState(false);
  const [peopleOptions, setPeopleOptions] = useState<PeopleOption[]>([]);
  const [accessRole, setAccessRole] = useState<{ role: string; menu_keys: string[] }>({ role: "", menu_keys: [] });
  const [open, setOpen] = useState(false),
    [editingDepartment, setEditingDepartment] = useState<Department | null>(
      null,
    ),
    [editingRole, setEditingRole] = useState<JobRole | null>(null),
    [permissionRole, setPermissionRole] = useState<JobRole | null>(null),
    [selectedRolePermissions, setSelectedRolePermissions] = useState<string[]>([]);
  const [selectedRoleFieldKeys, setSelectedRoleFieldKeys] = useState<string[]>([]);
  const [roleFieldKeysConfigured, setRoleFieldKeysConfigured] = useState(false);
  const [roleDataScope, setRoleDataScope] = useState<string | undefined>(undefined);
  const [availableRoleFieldKeys, setAvailableRoleFieldKeys] = useState<string[]>([]);
  const [availableRoleDataScopes, setAvailableRoleDataScopes] = useState<string[]>([]);
  const [rolePermissionTreeData, setRolePermissionTreeData] = useState<TreeDataNode[]>(permissionTreeData);
  const [rolePermissionLoading, setRolePermissionLoading] = useState(false);
  const [departmentForm] = Form.useForm(),
    [roleForm] = Form.useForm(),
    [createDepartmentForm] = Form.useForm();
  // 人事中心“部门新建”“部门设置”是两个单独菜单（思法汇成 10-31 16:44，BUG20261031002）。
  const createView = initialView === "hr-department-new";
  useEffect(() => {
    if (createView && !createDepartmentForm.isFieldTouched("sort_order"))
      createDepartmentForm.setFieldsValue({ sort_order: departments.length + 1 });
  }, [createView, departments.length]);
  const [creatingDepartment, setCreatingDepartment] = useState(false);
  const createDepartment = async () => {
    if (!canManageOrganization) {
      message.error("仅系统管理员可以新建部门");
      return;
    }
    try {
      const value = await createDepartmentForm.validateFields();
      setCreatingDepartment(true);
      await api.post("/hr/departments", { ...value, is_active: true, manager: "", owner_username: "", parent_department_id: null });
      message.success("部门已新建，请到人事中心“部门设置”里设置上级部门和负责人。");
      createDepartmentForm.resetFields();
      void load();
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || "新建失败.");
    } finally {
      setCreatingDepartment(false);
    }
  };
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
    void api.get<{ items?: PeopleOption[] }>("/people/options")
      .then(({ data }) => setPeopleOptions(data.items || []))
      .catch(() => setPeopleOptions([]));
    void api.get("/auth/me").then(({ data }) => setAccessRole({
      role: String(data.role || ""),
      menu_keys: Array.isArray(data.menu_keys) ? data.menu_keys.map(String) : [],
    })).catch(() => setAccessRole({ role: "", menu_keys: [] }));
  }, []);
  const canManageOrganization = organizationActionAccess(accessRole).canManageOrganization;
  const departmentTreeData = useMemo<TreeDataNode[]>(() => {
    const byParent = new Map<number | null, Department[]>();
    for (const department of departments) {
      const parentId = department.parent_department_id && departments.some((candidate) => candidate.id === department.parent_department_id)
        ? department.parent_department_id
        : null;
      const siblings = byParent.get(parentId) || [];
      siblings.push(department);
      byParent.set(parentId, siblings);
    }
    const build = (parentId: number | null, trail: Set<number>): TreeDataNode[] =>
      (byParent.get(parentId) || []).map((department) => {
        const nextTrail = new Set(trail).add(department.id);
        const children = nextTrail.has(department.parent_department_id || 0)
          ? []
          : build(department.id, nextTrail);
        return {
          key: `department:${department.id}`,
          title: `${department.name}（${department.code}）${department.is_active ? "" : "（停用）"}`,
          children,
        };
      });
    return build(null, new Set());
  }, [departments]);
  const start = (row?: Department | JobRole) => {
    if (!canManageOrganization) {
      message.error("仅系统管理员可以维护部门和角色");
      return;
    }
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
          sort_order: departments.length + 1,
          is_active: true,
        },
      );
    }
    setOpen(true);
  };
  const save = async () => {
    if (!canManageOrganization) {
      message.error("仅系统管理员可以维护部门和角色");
      return;
    }
    try {
      if (rolesView) {
        const value = await roleForm.validateFields();
        if (editingRole)
          await api.patch(`/hr/job-roles/${editingRole.id}`, value);
        else await api.post("/hr/job-roles", value);
        notifyPermissionsUpdated();
      } else {
        const fields = await departmentForm.validateFields();
        // 清空的选择框不会出现在表单值里，显式传空才能清掉负责人、上级部门和挂靠人。
        const value = {
          ...fields,
          parent_department_id: fields.parent_department_id ?? null,
          manager: fields.manager ?? "",
          owner_username: fields.parent_department_id ? fields.owner_username ?? "" : "",
        };
        if (editingDepartment)
          await api.patch(`/hr/departments/${editingDepartment.id}`, value);
        else await api.post("/hr/departments", value);
      }
      message.success("保存成功.");
      setOpen(false);
      void load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "保存失败.");
    }
  };
  const removeDepartment = async (row: Department) => {
    if (!canManageOrganization) {
      message.error("仅系统管理员可以停用部门");
      return;
    }
    // BUG20261031002：删除部门改为停用，历史数据保留。
    const childCount = departments.filter((candidate) => candidate.parent_department_id === row.id && candidate.is_active).length;
    if (childCount > 0) {
      message.error(`存在 ${childCount} 个启用的下级部门，请先停用或调整下级部门`);
      return;
    }
    try {
      await api.delete(`/hr/departments/${row.id}`);
      message.success("已停用.");
      void load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "停用失败.");
    }
  };
  const removeRole = async (row: JobRole) => {
    if (!canManageOrganization) {
      message.error("仅系统管理员可以删除角色");
      return;
    }
    if (row.code === "SYSTEM-ADMIN") {
      message.error("系统管理员角色不可删除");
      return;
    }
    try {
      await api.delete(`/hr/job-roles/${row.id}`);
      notifyPermissionsUpdated();
      message.success("删除成功.");
      void load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败.");
    }
  };
  const openRolePermissions = async (row: JobRole) => {
    if (!canManageOrganization) {
      message.error("仅系统管理员可以设置角色权限");
      return;
    }
    setPermissionRole(row);
    setSelectedRolePermissions(rolePermissionsToTreeCheckedKeys(row.permissions || [], permissionTreeData));
    setSelectedRoleFieldKeys(row.field_keys || []);
    setRoleFieldKeysConfigured(Boolean(row.field_keys_configured));
    setRoleDataScope(row.data_scope || undefined);
    setRolePermissionTreeData(permissionTreeData);
    setRolePermissionLoading(true);
    try {
      const { data } = await api.get(`/hr/job-roles/${row.id}/permissions`);
      const nextRolePermissionTreeData = data.tree || permissionTreeData;
      setRolePermissionTreeData(nextRolePermissionTreeData);
      setSelectedRolePermissions(rolePermissionsToTreeCheckedKeys(data.checked_permissions || data.permissions || row.permissions || [], nextRolePermissionTreeData));
      setSelectedRoleFieldKeys(data.field_keys || []);
      setRoleFieldKeysConfigured(Boolean(data.field_keys_configured));
      setRoleDataScope(data.data_scope || undefined);
      setAvailableRoleFieldKeys(data.available_field_keys || []);
      setAvailableRoleDataScopes(data.available_data_scopes || []);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "角色权限加载失败");
    } finally {
      setRolePermissionLoading(false);
    }
  };
  const saveRolePermissions = async () => {
    if (!permissionRole) return;
    if (!canManageOrganization) {
      message.error("仅系统管理员可以设置角色权限");
      return;
    }
    if (permissionRole.code === "SYSTEM-ADMIN") {
      message.error("系统管理员权限不可修改");
      return;
    }
    try {
      await api.patch(`/hr/job-roles/${permissionRole.id}/permissions`, {
        permissions: rolePermissionTreeKeysToPayload(selectedRolePermissions),
        case_actions_explicit: true,
        field_keys: selectedRoleFieldKeys,
        field_keys_configured: roleFieldKeysConfigured,
        data_scope: roleDataScope || "",
      });
      message.success("角色权限已保存.");
      notifyPermissionsUpdated();
      setPermissionRole(null);
      void load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "角色权限保存失败.");
    }
  };
  const departmentColumns: TableColumnsType<Department> = [
    { title: "序号", key: "no", width: 70, render: (_v, _r, i) => i + 1 },
    { title: "部门名称", dataIndex: "name", width: 180 },
    { title: "部门代码", dataIndex: "code", width: 150 },
    { title: "上级部门", dataIndex: "parent_department_name", width: 160, render: (value) => value || "—" },
    { title: "是否逾期扣款", dataIndex: "overdue_deduction", width: 120, render: (value) => value ? "是" : "否" },
    {
      title: "部门负责人",
      dataIndex: "manager",
      width: 130,
      render: (_value, row) => renderPersonReference(row.manager_display_name, row.manager_display_name_missing),
    },
    {
      title: "挂靠人",
      dataIndex: "owner_username",
      width: 120,
      render: (_value, row) => row.owner_username ? renderPersonReference(row.owner_display_name, row.owner_display_name_missing) : "—",
    },
    { title: "排序", dataIndex: "sort_order", width: 75 },
    { title: "创建人", dataIndex: "created_by", width: 120, render: (_value, row) => renderPersonReference(row.created_by_display_name, row.created_by_display_name_missing) },
    { title: "更新人", dataIndex: "updated_by", width: 120, render: (_value, row) => renderPersonReference(row.updated_by_display_name, row.updated_by_display_name_missing) },
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
      render: (_v, row) => canManageOrganization ? (
        <Space size={0}>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => start(row)}
          >
            修改
          </Button>
          {row.is_active ? (
            <Popconfirm
              title="确认停用该部门？停用后不能再选择，历史数据保留。"
              onConfirm={() => removeDepartment(row)}
            >
              <Button type="link" danger>停用</Button>
            </Popconfirm>
          ) : null}
        </Space>
      ) : "—",
    },
  ];
  const roleColumns: TableColumnsType<JobRole> = [
    { title: "序号", key: "no", width: 70, render: (_v, _r, i) => i + 1 },
    { title: "角色名称", dataIndex: "name", width: 240 },
    { title: "角色代码", dataIndex: "code", width: 150 },
    { title: "说明", dataIndex: "description", width: 220, render: (value) => value || "—" },
    { title: "排序", dataIndex: "sort_order", width: 75 },
    { title: "可用", dataIndex: "is_active", width: 75, render: (value) => (value ? "是" : "否") },
    { title: "更新人", dataIndex: "updated_by", width: 120, render: (_value, row) => renderPersonReference(row.updated_by_display_name, row.updated_by_display_name_missing) },
    {
      title: "角色权限",
      key: "permissions",
      render: (_v, row) => canManageOrganization ? <Button type="link" onClick={() => openRolePermissions(row)}>权限设定</Button> : "—",
    },
    {
      title: "操作",
      key: "action",
      width: 170,
      render: (_v, row) => canManageOrganization ? (
        <Space size={0}>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => start(row)}
          >
            修改
          </Button>
          {canDeleteOrganizationRole(row.code) && (
            <Popconfirm
              title="确认删除该角色？"
              onConfirm={() => removeRole(row)}
            >
              <Button type="link" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ) : "—",
    },
  ];
  const title = rolesView ? "角色列表" : "部门设置",
    button = rolesView ? "新增角色" : "新增部门";
  const [organizationPage, setOrganizationPage] = useState(1);
  const [organizationPageSize, setOrganizationPageSize] = useState(15);
  const emptyContent = (
    <div className="organization-empty">
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
      {canManageOrganization && (
        rolesView ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => start()}>
            {button}
          </Button>
        ) : <span>请在人事中心“部门新建”里新建部门</span>
      )}
    </div>
  );
  const createDepartmentPanel = (
    <Form form={createDepartmentForm} layout="vertical" className="organization-create-form" initialValues={{ sort_order: departments.length + 1 }}>
      <Alert type="info" showIcon style={{ marginBottom: 16 }} title="这里只新建部门；上级部门、部门负责人、挂靠人和停用都在人事中心“部门设置”里操作。" />
      <div className="organization-form-grid">
        <Form.Item label="部门名称" name="name" rules={[{ required: true, message: "请输入部门名称." }]}>
          <Input />
        </Form.Item>
        <Form.Item label="部门代码" name="code" rules={[{ required: true, message: "请输入部门代码." }]}>
          <Input />
        </Form.Item>
        <Form.Item label="排序号" name="sort_order" rules={[{ required: true }]}>
          <InputNumber min={0} style={{ width: "100%" }} />
        </Form.Item>
      </div>
      <Button type="primary" icon={<PlusOutlined />} loading={creatingDepartment} disabled={!canManageOrganization} onClick={() => void createDepartment()}>
        新建部门
      </Button>
    </Form>
  );
  if (createView) {
    return (
      <Card className="panel organization-panel" title="部门新建">
        {createDepartmentPanel}
      </Card>
    );
  }
  return (
    <>
      <Card className="panel organization-panel" title={title}>
        <div className="organization-action">
          {canManageOrganization && rolesView && <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => start()}
          >
            {button}
          </Button>}
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
              current: organizationPage,
              pageSize: organizationPageSize,
              showSizeChanger: true,
              pageSizeOptions: ["10", "15", "20", "50", "100"],
              showQuickJumper: { goButton: "GO" },
              showTotal: (total) => `共 ${total} 条`,
              onChange: (page, pageSize) => { setOrganizationPage(page); setOrganizationPageSize(pageSize); },
            }}
          />
        ) : (
          <Table
            rowKey="id"
            size="small"
            loading={loading}
            columns={departmentColumns}
            dataSource={departments}
            scroll={{ x: 960 }}
            locale={{ emptyText: emptyContent }}
            pagination={{
              current: organizationPage,
              pageSize: organizationPageSize,
              showSizeChanger: true,
              pageSizeOptions: ["10", "15", "20", "50", "100"],
              showQuickJumper: { goButton: "GO" },
              showTotal: (total) => `共 ${total} 条`,
              onChange: (page, pageSize) => { setOrganizationPage(page); setOrganizationPageSize(pageSize); },
            }}
          />
        )}
      </Card>
      {!rolesView && (
        <Card className="panel organization-tree-panel" size="small" title="组织树">
          {departmentTreeData.length ? (
            <Tree defaultExpandAll treeData={departmentTreeData} />
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无组织层级" />
          )}
        </Card>
      )}
      <Modal
        open={open}
        title={`${editingDepartment || editingRole ? "修改" : "新增"}${rolesView ? "角色" : "部门"}`}
        okText="保存"
        cancelText="取消"
        onOk={save}
        onCancel={() => setOpen(false)}
        destroyOnHidden
        width={POPUP_WIDTH.md}
      >
        {rolesView ? (
          <Form form={roleForm} layout="vertical">
            <div className="organization-form-grid">
              <Form.Item
                label="角色名称"
                name="name"
                rules={[{ required: true, message: "请输入角色名称." }]}
              >
                <Input disabled={editingRole?.code === "SYSTEM-ADMIN"} />
              </Form.Item>
              <Form.Item
                label="角色代码"
                name="code"
                rules={[{ required: true, message: "请输入角色代码." }]}
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
              <Form.Item className="span-2" label="说明" name="description" rules={[{ required: true, message: "请输入角色名称描述." }]}>
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
                  title="部门只维护组织和数据归属"
                  description="菜单和业务动作权限统一在“角色管理”中配置；部门用于组织归属及部门范围的数据查看。"
                />
              </Form.Item>
              <Form.Item
                label="部门名称"
                name="name"
                rules={[{ required: true, message: "请输入部门名称." }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                label="部门代码"
                name="code"
                rules={[{ required: true, message: "请输入部门代码." }]}
              >
                <Input />
              </Form.Item>
              <Form.Item label="上级部门" name="parent_department_id">
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  placeholder="请选择（顶级部门）"
                  options={departments.filter((candidate) => candidate.is_active && candidate.id !== editingDepartment?.id).map((candidate) => ({ value: candidate.id, label: candidate.name }))}
                />
              </Form.Item>
              <Form.Item label="部门负责人" name="manager" extra="一个人可以兼任多个部门的负责人">
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="search"
                  placeholder="请选择"
                  options={peopleOptions.map((person) => ({ value: person.username, label: person.label, search: person.search_text || person.label }))}
                />
              </Form.Item>
              <Form.Item noStyle dependencies={["parent_department_id"]}>
                {({ getFieldValue }) => getFieldValue("parent_department_id") ? (
                  <Form.Item label="挂靠人" name="owner_username" extra="这个下级部门归谁管；挂靠人和他的上级能看这个部门的数据，同部门其他人看不到">
                    <Select
                      allowClear
                      showSearch
                      optionFilterProp="search"
                      placeholder="请选择"
                      options={peopleOptions.map((person) => ({ value: person.username, label: person.label, search: person.search_text || person.label }))}
                    />
                  </Form.Item>
                ) : null}
              </Form.Item>
              <Form.Item label="是否逾期扣款" name="overdue_deduction" valuePropName="checked">
                <Switch checkedChildren="是" unCheckedChildren="否" />
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
            confirmLoading={rolePermissionLoading}
        destroyOnHidden
        width={POPUP_WIDTH.sm}
      >
        <Form layout="horizontal" labelCol={{ span: 7 }} wrapperCol={{ span: 15 }}>
          <Form.Item label="角色名称">
            <Input value={permissionRole?.name || ""} readOnly />
          </Form.Item>
          <Form.Item label="菜单及动作权限">
            <div className="legacy-role-permission-tree">
              <Tree
                checkable
                checkStrictly
                defaultExpandAll
                    treeData={rolePermissionTreeData}
                    checkedKeys={rolePermissionCheckedGroups(rolePermissionTreeData, selectedRolePermissions)}
                disabled={rolePermissionLoading || permissionRole?.code === "SYSTEM-ADMIN"}
                onCheck={(_checked, info) => {
                  const key = String(info.node.key);
                  // BUG20261028012：案件三块（group:）勾选即全选块下功能，块下每个功能也可单独勾选。
                  const affected = key.startsWith("menu:") || key.startsWith("group:")
                    ? rolePermissionMenuBranch(rolePermissionTreeData, key)
                    : [roleActionBaseKey(key)];
                  setSelectedRolePermissions((current) => {
                    const next = new Set(current);
                    affected.forEach((item) => info.checked ? next.add(item) : next.delete(item));
                    return normalizeRolePermissionCheckedKeys(Array.from(next));
                  });
                }}
              />
            </div>
          </Form.Item>
          <Form.Item label="数据范围">
            <Select
              allowClear
              placeholder="继承系统账号角色范围"
              value={roleDataScope}
              disabled={permissionRole?.code === "SYSTEM-ADMIN"}
              options={availableRoleDataScopes.map((value) => ({ value, label: value }))}
              onChange={(value) => setRoleDataScope(value)}
            />
          </Form.Item>
          <Form.Item label="字段权限">
            <Space direction="vertical" style={{ width: "100%" }}>
              <Switch
                checked={roleFieldKeysConfigured}
                checkedChildren="自定义"
                unCheckedChildren="继承"
                disabled={permissionRole?.code === "SYSTEM-ADMIN"}
                onChange={setRoleFieldKeysConfigured}
              />
              <Select
                mode="multiple"
                allowClear
                placeholder={roleFieldKeysConfigured ? "选择可见字段；留空表示不授予受控字段" : "继承系统账号角色字段"}
                value={selectedRoleFieldKeys}
                disabled={!roleFieldKeysConfigured || permissionRole?.code === "SYSTEM-ADMIN"}
                options={availableRoleFieldKeys.map((value) => ({ value, label: value }))}
                onChange={setSelectedRoleFieldKeys}
              />
            </Space>
          </Form.Item>
          {permissionRole?.code === "SYSTEM-ADMIN" && <Form.Item wrapperCol={{ offset: 7, span: 15 }}><Alert type="info" showIcon title="系统管理员权限由系统强制保持完整，不能在此降权。" /></Form.Item>}
        </Form>
      </Modal>
    </>
  );
}
