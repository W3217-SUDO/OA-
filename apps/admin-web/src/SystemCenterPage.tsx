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
  Table,
  Tag,
  TreeSelect,
} from "antd";
import type { TableColumnsType } from "antd";
import {
  ClearOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { api } from "./api";
import "./system-center.css";

type ParameterRow = {
  id: number;
  category: string;
  code: string;
  name: string;
  extra: Record<string, any>;
  sort_order: number;
  is_active: boolean;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
};
type SystemConfig = {
  key: string;
  label: string;
  group: string;
  value: Record<string, any>;
  description: string;
  updated_by: string;
  updated_at: string;
};
type CacheRow = {
  key: string;
  name: string;
  description: string;
  entry_count: number;
  bucket_count: number;
  last_cleared_at: string | null;
  last_cleared_by: string;
};
type MenuRow = {
  id: number;
  key: string;
  parent_key: string;
  label: string;
  description: string;
  icon: string;
  sort_order: number;
  is_visible: boolean;
  is_active: boolean;
  is_system: boolean;
  updated_by: string;
  updated_at: string;
};
type SystemUser = {
  id: number;
  username: string;
  display_name: string;
  department: string;
  role: string;
  is_active: boolean;
  must_change_password?: boolean;
  contract_approval_enabled?: boolean;
  profile?: Record<string, any>;
  email: string;
  mobile: string;
  office_phone: string;
  failed_login_attempts: number;
  locked_until: string | null;
  last_login_at: string | null;
  created_at: string;
};
type RolePermission = {
  role: string;
  display_name: string;
  data_scope: string;
  menu_keys: string[];
  field_keys: string[];
  updated_at: string;
};
type SecurityPolicy = {
  min_password_length: number;
  max_failed_attempts: number;
  lock_minutes: number;
  token_minutes: number;
  updated_by: string;
  updated_at: string;
};

const categoryByRoute: Record<string, string> = {
  "system-parameters-case-type": "case_type",
  "system-parameters-fee-type": "fee_type",
  "system-parameters-case-phase": "case_phase",
  "system-parameters-court": "court",
  "system-parameters-notary-office": "notary_office",
  "system-parameters-cause": "cause",
  "system-parameters-payment": "payment_type",
  "system-parameters-customer-type": "customer_type",
  "system-parameters-case-file-type": "case_file_type",
  "system-parameters-ipr-case-file-type": "ipr_case_file_type",
  "system-parameters-district": "district",
  "system-parameters-court-officer": "court_officer",
};
const categoryTitle: Record<string, string> = {
  case_type: "案件类型",
  fee_type: "费用类型",
  case_phase: "案件阶段",
  court: "法院",
  notary_office: "公证处",
  cause: "案由",
  payment_type: "付款类型",
  customer_type: "客户类型",
  case_file_type: "案件文件类型",
  district: "地区",
  court_officer: "法院工作人员",
};
const categoryPlaceholder: Record<string, string> = {
  case_type: "案件类型名称",
  fee_type: "费用类型名称",
  case_phase: "案件阶段名称",
  court: "法院名称",
  notary_office: "公证处名称",
  cause: "案由名称",
  payment_type: "付款类型名称",
  customer_type: "客户类型名称",
  case_file_type: "案件文件类型名称",
  district: "地区名称",
  court_officer: "工作人员姓名",
};
categoryTitle.ipr_case_file_type = "知识产权案件文件类型";
categoryPlaceholder.ipr_case_file_type = "知识产权案件文件类型名称";
const extraFields: Record<string, { key: string; label: string }[]> = {
  case_type: [{ key: "letter_code", label: "类型字母名称" }],
  fee_type: [{ key: "group", label: "类型大类" }],
  case_phase: [
    { key: "parent_code", label: "上级阶段Id" },
    { key: "case_type", label: "案件类型" },
  ],
  notary_office: [{ key: "number_template", label: "公证号模板" }],
  cause: [{ key: "parent_code", label: "上级案由Id" }],
  payment_type: [
    { key: "nature", label: "付款性质" },
    { key: "payee", label: "收款单位" },
    { key: "account", label: "账号" },
  ],
  case_file_type: [{ key: "parent_code", label: "上级文件类型代码" }],
  district: [{ key: "parent_code", label: "上级地区代码" }],
  court_officer: [
    { key: "court_code", label: "法院代码" },
    { key: "role", label: "职务" },
    { key: "phone", label: "联系电话" },
  ],
};
const formatTime = (value: string) =>
  value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "—";

export function sanitizeShareDaysInput(value: unknown): string {
  return String(value ?? "").replace(/\D/g, "");
}

export function cleanShareDaysInputEvent(event: {
  currentTarget: { value: string };
}): string {
  const sanitized = sanitizeShareDaysInput(event.currentTarget.value);
  event.currentTarget.value = sanitized;
  return sanitized;
}

export function isShareDaysValueValid(value: unknown): boolean {
  const normalized = sanitizeShareDaysInput(value);
  if (!normalized || normalized !== String(value ?? "")) return false;
  const days = Number(normalized);
  return Number.isInteger(days) && days >= 1 && days <= 3650;
}

export function sanitizeCompanyDigitsInput(value: unknown): string {
  return String(value ?? "").replace(/\D/g, "");
}

export function cleanCompanyDigitsInputEvent(event: {
  currentTarget: { value: string };
}): string {
  const sanitized = sanitizeCompanyDigitsInput(event.currentTarget.value);
  event.currentTarget.value = sanitized;
  return sanitized;
}

export default function SystemCenterPage({
  initialView = "system-parameters",
}: {
  initialView?: string;
}) {
  const category = categoryByRoute[initialView] || "";
  const [parameters, setParameters] = useState<ParameterRow[]>([]);
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [caches, setCaches] = useState<CacheRow[]>([]);
  const [cacheTotal, setCacheTotal] = useState(0);
  const [cachePage, setCachePage] = useState(1);
  const [cachePageSize, setCachePageSize] = useState(15);
  const [selectedCacheKeys, setSelectedCacheKeys] = useState<string[]>([]);
  const [menus, setMenus] = useState<MenuRow[]>([]);
  const [menuPage, setMenuPage] = useState(1);
  const [menuPageSize, setMenuPageSize] = useState(15);
  const [menuSearchInput, setMenuSearchInput] = useState("");
  const [menuSearch, setMenuSearch] = useState("");
  const [users, setUsers] = useState<SystemUser[]>([]),
    [rolePermissions, setRolePermissions] = useState<RolePermission[]>([]);
  const [availableMenuKeys, setAvailableMenuKeys] = useState<string[]>([]),
    [availableFieldKeys, setAvailableFieldKeys] = useState<string[]>([]);
  const [securityPolicy, setSecurityPolicy] = useState<SecurityPolicy | null>(
    null,
  );
  const [keyword, setKeyword] = useState("");
  const [currentUsername, setCurrentUsername] = useState("");
  const [secondaryKeyword, setSecondaryKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [parameterOpen, setParameterOpen] = useState(false);
  const [editingParameter, setEditingParameter] = useState<ParameterRow | null>(
    null,
  );
  const [menuOpen, setMenuOpen] = useState(false);
  const [editingMenu, setEditingMenu] = useState<MenuRow | null>(null);
  const [userOpen, setUserOpen] = useState(false),
    [editingUser, setEditingUser] = useState<SystemUser | null>(null);
  const [resettingUser, setResettingUser] = useState<SystemUser | null>(null);
  const [roleOpen, setRoleOpen] = useState(false),
    [editingRole, setEditingRole] = useState<RolePermission | null>(null);
  const [parameterForm] = Form.useForm(),
    [shareForm] = Form.useForm(),
    [companyForm] = Form.useForm(),
    [menuForm] = Form.useForm(),
    [userForm] = Form.useForm(),
    [resetPasswordForm] = Form.useForm(),
    [roleForm] = Form.useForm(),
    [securityForm] = Form.useForm();

  const loadParameters = async (search = keyword) => {
    if (!category) return;
    setLoading(true);
    try {
      const { data } = await api.get("/system/parameters", {
        params: { category, keyword: search },
      });
      setParameters(data.items);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "系统参数加载失败");
    } finally {
      setLoading(false);
    }
  };
  const loadConfigs = async () => {
    try {
      const { data } = await api.get("/system/configs");
      setConfigs(data.items);
      for (const item of data.items as SystemConfig[]) {
        if (
          item.key === "customer_share_policy" &&
          initialView === "system-parameters"
        )
          shareForm.setFieldsValue(item.value);
        if (
          item.key === "company_profile" &&
          initialView === "system-parameters-company"
        )
          companyForm.setFieldsValue(item.value);
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "系统配置加载失败");
    }
  };
  const loadCaches = async (page = cachePage, pageSize = cachePageSize) => {
    try {
      const { data } = await api.get("/system/caches", { params: { page, page_size: pageSize } });
      setCaches(data.items);
      setCacheTotal(data.total ?? data.items.length);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "缓存加载失败");
    }
  };
  const loadMenus = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/system/menus");
      setMenus(data.items);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "菜单加载失败");
    } finally {
      setLoading(false);
    }
  };
  const loadUsers = async (search = "") => {
    setLoading(true);
    try {
      const { data } = await api.get("/system/users", {
        params: { keyword: search },
      });
      setUsers(data.items);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "系统用户加载失败");
    } finally {
      setLoading(false);
    }
  };
  const loadRoles = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/system/role-permissions");
      setRolePermissions(data.items);
      setAvailableMenuKeys(data.available_menu_keys);
      setAvailableFieldKeys(data.available_field_keys);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "角色权限加载失败");
    } finally {
      setLoading(false);
    }
  };
  const loadSecurity = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/system/security-policy");
      setSecurityPolicy(data);
      securityForm.setFieldsValue(data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "安全策略加载失败");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    setKeyword("");
    setSecondaryKeyword("");
    setMenuPage(1);
    setMenuSearchInput("");
    setMenuSearch("");
    if (initialView === "system-users")
      void api
        .get("/auth/me")
        .then(({ data }) => setCurrentUsername(data.username))
        .catch(() => setCurrentUsername(""));
    if (category) void loadParameters("");
    else if (
      initialView === "system-parameters" ||
      initialView === "system-parameters-company" ||
      initialView === "system-management-config"
    )
      void loadConfigs();
    else if (initialView === "system-management-cache") void loadCaches();
    else if (initialView === "system-management-menu") void loadMenus();
    else if (initialView === "system-users") void loadUsers();
    else if (initialView === "system-roles") {
      void loadRoles();
      void loadMenus();
    } else if (initialView === "system-security") void loadSecurity();
  }, [initialView, category]);

  const saveConfig = async (
    key: string,
    target: ReturnType<typeof Form.useForm>[0],
  ) => {
    const value: any = await target.validateFields();
    try {
      const { data } = await api.patch(`/system/configs/${key}`, { value });
      setConfigs((items) =>
        items.map((item) => (item.key === key ? data : item)),
      );
      message.success("保存成功");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "保存失败");
    }
  };
  const startParameter = (row?: ParameterRow) => {
    setEditingParameter(row || null);
    parameterForm.resetFields();
    parameterForm.setFieldsValue(
      row
        ? {
            ...row,
            ...row.extra,
            hedging_file_type_codes: (
              row.extra.hedging_file_type_codes || []
            ).join(","),
            hedging_fee_type_codes: (
              row.extra.hedging_fee_type_codes || []
            ).join(","),
          }
        : {
            sort_order: parameters.length + 1,
            is_active: true,
            case_kinds: ["专利", "商标"],
            allow_repeat: true,
          },
    );
    setParameterOpen(true);
  };
  const saveParameter = async () => {
    const value = await parameterForm.validateFields();
    const extra =
      category === "ipr_case_file_type"
        ? {
            case_kinds: value.case_kinds || [],
            is_official: false,
            requires_transmission: !!value.requires_transmission,
            allow_repeat: value.allow_repeat !== false,
            hedging_file_type_codes: (value.hedging_file_type_codes || "")
              .split(",")
              .map((v: string) => v.trim())
              .filter(Boolean),
            hedging_fee_type_codes: (value.hedging_fee_type_codes || "")
              .split(",")
              .map((v: string) => v.trim())
              .filter(Boolean),
          }
        : Object.fromEntries(
            (extraFields[category] || []).map((item) => [
              item.key,
              value[item.key] || "",
            ]),
          );
    const payload = {
      category,
      code: value.code,
      name: value.name,
      sort_order: value.sort_order,
      is_active: value.is_active,
      extra,
    };
    try {
      if (editingParameter)
        await api.patch(`/system/parameters/${editingParameter.id}`, {
          code: payload.code,
          name: payload.name,
          sort_order: payload.sort_order,
          is_active: payload.is_active,
          extra,
        });
      else await api.post("/system/parameters", payload);
      message.success(editingParameter ? "修改成功" : "新增成功");
      setParameterOpen(false);
      void loadParameters("");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "保存失败");
    }
  };
  const removeParameter = async (row: ParameterRow) => {
    try {
      await api.delete(`/system/parameters/${row.id}`);
      message.success("删除成功");
      void loadParameters("");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const clearCache = async (row: CacheRow) => {
    try {
      await api.post(`/system/caches/${row.key}/clear`);
      message.success("缓存已清空");
      setSelectedCacheKeys((keys) => keys.filter((key) => key !== row.key));
      void loadCaches(cachePage, cachePageSize);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "清理失败");
    }
  };
  const clearSelectedCaches = async () => {
    if (!selectedCacheKeys.length) {
      message.info("请先选择要清除的缓存");
      return;
    }
    try {
      await api.post("/system/caches/clear", { cache_keys: selectedCacheKeys });
      message.success(`已清除 ${selectedCacheKeys.length} 项缓存`);
      setSelectedCacheKeys([]);
      void loadCaches(cachePage, cachePageSize);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "批量清除缓存失败");
    }
  };
  const editMenu = (row: MenuRow) => {
    setEditingMenu(row);
    menuForm.resetFields();
    menuForm.setFieldsValue(row);
    setMenuOpen(true);
  };
  const saveMenu = async () => {
    const value = await menuForm.validateFields();
    try {
      const { data } = editingMenu
        ? await api.patch(`/system/menus/${editingMenu.id}`, value)
        : await api.post("/system/menus", value);
      message.success(editingMenu ? "菜单已修改" : "菜单已新增");
      setMenuOpen(false);
      window.dispatchEvent(new Event("sunhold:menus-updated"));
      setMenus((items) =>
        editingMenu
          ? items.map((item) => (item.id === data.id ? data : item))
          : [...items, data],
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "保存失败");
    }
  };
  const removeMenu = async (row: MenuRow) => {
    try {
      await api.delete(`/system/menus/${row.id}`);
      message.success("历史菜单已删除");
      window.dispatchEvent(new Event("sunhold:menus-updated"));
      void loadMenus();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "删除失败");
    }
  };
  const editUser = (row?: SystemUser) => {
    setEditingUser(row || null);
    userForm.resetFields();
    userForm.setFieldsValue(
      row
        ? {
            ...row,
            password: "",
            profile: {
              ...(row.profile || {}),
              email: row.email || "",
              mobile: row.mobile || "",
              office_phone: row.office_phone || "",
              contract_approval_enabled: !!row.contract_approval_enabled,
            },
          }
        : {
            department: "上海分所",
            role: "user",
            is_active: true,
            profile: { contract_approval_enabled: false },
          },
    );
    setUserOpen(true);
  };
  const saveUser = async () => {
    const value = await userForm.validateFields();
    const payload = { ...value, profile: value.profile || {} };
    if (editingUser && !payload.password) delete payload.password;
    if (!editingUser) payload.must_change_password = true;
    try {
      if (editingUser)
        await api.patch(`/system/users/${editingUser.id}`, payload);
      else await api.post("/system/users", payload);
      message.success(
        editingUser ? "账号已更新" : "账号已创建，首次登录必须修改初始密码",
      );
      setUserOpen(false);
      void loadUsers(keyword);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "账号保存失败");
    }
  };
  const removeUser = async (row: SystemUser) => {
    try {
      await api.delete(`/system/users/${row.id}`);
      message.success("账号已删除");
      void loadUsers(keyword);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "账号删除失败");
    }
  };
  const openPasswordReset = (row: SystemUser) => {
    resetPasswordForm.resetFields();
    setResettingUser(row);
  };
  const resetPassword = async () => {
    if (!resettingUser) return;
    try {
      const value = await resetPasswordForm.validateFields();
      await api.post(`/system/users/${resettingUser.id}/reset-password`, {
        new_password: value.new_password,
      });
      message.success("密码已重置，用户下次登录必须修改密码");
      setResettingUser(null);
      resetPasswordForm.resetFields();
      void loadUsers(keyword);
    } catch (error: any) {
      if (error?.errorFields) return;
      message.error(error?.response?.data?.detail || "密码重置失败");
    }
  };
  const unlockUser = async (row: SystemUser) => {
    try {
      await api.post(`/system/users/${row.id}/unlock`);
      message.success("账号已解锁并清除失败次数");
      void loadUsers(keyword);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "账号解锁失败");
    }
  };
  const editRole = (row: RolePermission) => {
    setEditingRole(row);
    roleForm.setFieldsValue(row);
    setRoleOpen(true);
  };
  const saveRole = async () => {
    if (!editingRole) return;
    const value = await roleForm.validateFields();
    try {
      await api.patch(`/system/role-permissions/${editingRole.role}`, value);
      message.success("角色权限已保存");
      setRoleOpen(false);
      void loadRoles();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "角色权限保存失败");
    }
  };
  const saveSecurity = async () => {
    const value = await securityForm.validateFields();
    try {
      const { data } = await api.patch("/system/security-policy", value);
      setSecurityPolicy(data);
      message.success("安全策略已保存");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "安全策略保存失败");
    }
  };

  const actionColumn = {
    title: "操作",
    key: "action",
    width: 120,
    render: (_value: unknown, row: ParameterRow) => (
      <Space size={0}>
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => startParameter(row)}
        >
          修改
        </Button>
        {category !== "case_type" && (
          <Popconfirm title="确认删除？" onConfirm={() => removeParameter(row)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        )}
      </Space>
    ),
  };
  const auditColumns = [
    { title: "创建人", dataIndex: "created_by", width: 90 },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 165,
      render: formatTime,
    },
    { title: "修改人", dataIndex: "updated_by", width: 90 },
    {
      title: "修改时间",
      dataIndex: "updated_at",
      width: 165,
      render: formatTime,
    },
  ];
  const parameterColumns = useMemo<TableColumnsType<ParameterRow>>(() => {
    if (category === "case_type")
      return [
        { title: "类型编号", dataIndex: "code", width: 120 },
        { title: "类型名称", dataIndex: "name", width: 180 },
        {
          title: "类型字母名称",
          key: "letter",
          width: 140,
          render: (_, r) => r.extra.letter_code || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "fee_type")
      return [
        { title: "类型代码", dataIndex: "code", width: 120 },
        { title: "类型名称", dataIndex: "name", width: 180 },
        {
          title: "类型大类",
          key: "group",
          width: 140,
          render: (_, r) => r.extra.group || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "case_phase")
      return [
        { title: "阶段Id", dataIndex: "code", width: 100 },
        { title: "案件阶段", dataIndex: "name", width: 150 },
        {
          title: "上级阶段Id",
          key: "parent",
          width: 110,
          render: (_, r) => r.extra.parent_code || "—",
        },
        {
          title: "案件类型",
          key: "caseType",
          width: 140,
          render: (_, r) => r.extra.case_type || "—",
        },
        { title: "排序号", dataIndex: "sort_order", width: 80 },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "court")
      return [
        { title: "序号", dataIndex: "sort_order", width: 70 },
        { title: "法院名称", dataIndex: "name", width: 220 },
        { title: "法院代码", dataIndex: "code", width: 140 },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "notary_office")
      return [
        { title: "公证处Id", dataIndex: "code", width: 110 },
        { title: "公证处名称", dataIndex: "name", width: 190 },
        { title: "公证处代码", dataIndex: "code", width: 130 },
        {
          title: "公证号模板",
          key: "template",
          width: 170,
          render: (_, r) => r.extra.number_template || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "cause")
      return [
        { title: "案由Id", dataIndex: "code", width: 100 },
        { title: "案由名称", dataIndex: "name", width: 210 },
        {
          title: "上级案由Id",
          key: "parent",
          width: 120,
          render: (_, r) => r.extra.parent_code || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "ipr_case_file_type")
      return [
        { title: "类型代码", dataIndex: "code", width: 150 },
        { title: "文件类型名称", dataIndex: "name", width: 220 },
        {
          title: "适用案件",
          key: "kinds",
          width: 140,
          render: (_, r) =>
            ((r.extra.case_kinds || []) as string[]).join("、") || "全部",
        },
        {
          title: "待转文",
          key: "transfer",
          width: 90,
          render: (_, r) => (r.extra.requires_transmission ? "是" : "否"),
        },
        {
          title: "允许重复",
          key: "repeat",
          width: 100,
          render: (_, r) => (r.extra.allow_repeat === false ? "否" : "是"),
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "case_file_type")
      return [
        { title: "文件类型代码", dataIndex: "code", width: 150 },
        { title: "文件类型名称", dataIndex: "name", width: 220 },
        {
          title: "上级文件类型代码",
          key: "parent",
          width: 160,
          render: (_, r) => r.extra.parent_code || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "district")
      return [
        { title: "地区代码", dataIndex: "code", width: 150 },
        { title: "地区名称", dataIndex: "name", width: 220 },
        {
          title: "上级地区代码",
          key: "parent",
          width: 150,
          render: (_, r) => r.extra.parent_code || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "customer_type")
      return [
        { title: "类型代码", dataIndex: "code", width: 150 },
        { title: "类型名称", dataIndex: "name", width: 220 },
        { title: "排序号", dataIndex: "sort_order", width: 90 },
        ...auditColumns,
        actionColumn,
      ];
    if (category === "court_officer")
      return [
        { title: "工作人员代码", dataIndex: "code", width: 150 },
        { title: "姓名", dataIndex: "name", width: 150 },
        {
          title: "法院代码",
          key: "court",
          width: 130,
          render: (_, r) => r.extra.court_code || "—",
        },
        {
          title: "职务",
          key: "role",
          width: 110,
          render: (_, r) => r.extra.role || "—",
        },
        {
          title: "联系电话",
          key: "phone",
          width: 150,
          render: (_, r) => r.extra.phone || "—",
        },
        ...auditColumns,
        actionColumn,
      ];
    return [
      { title: "序号", dataIndex: "sort_order", width: 70 },
      { title: "付款类型名", dataIndex: "name", width: 160 },
      {
        title: "付款性质",
        key: "nature",
        width: 130,
        render: (_, r) => r.extra.nature || "—",
      },
      {
        title: "收款单位",
        key: "payee",
        width: 190,
        render: (_, r) => r.extra.payee || "—",
      },
      {
        title: "账号",
        key: "account",
        width: 170,
        render: (_, r) => r.extra.account || "—",
      },
      actionColumn,
    ];
  }, [category, parameters.length]);

  const empty = (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
  );
  const menuTreeData = useMemo(() => {
    const nodes = new Map<string, any>();
    menus.forEach((row) =>
      nodes.set(row.key, {
        title: row.label,
        value: row.key,
        key: row.key,
        children: [],
      }),
    );
    const roots: any[] = [];
    menus.forEach((row) => {
      const node = nodes.get(row.key);
      const parent = row.parent_key ? nodes.get(row.parent_key) : undefined;
      if (parent) parent.children.push(node);
      else roots.push(node);
    });
    return roots;
  }, [menus]);
  let content: React.ReactNode;
  if (category) {
    const title = `${categoryTitle[category]}列表`;
    const usesParentCode = ["cause", "case_file_type", "district"].includes(
      category,
    );
    const visibleParameters = parameters.filter(
      (row) =>
        !secondaryKeyword ||
        (category === "court"
          ? row.code.includes(secondaryKeyword)
          : String(row.extra.parent_code || "").includes(secondaryKeyword)),
    );
    content = (
      <Card className="panel system-focused" title={title}>
        <div className="system-query">
          <label>
            <span>
              {category === "court"
                ? "法院名称"
                : usesParentCode
                  ? `${categoryTitle[category]}名称`
                  : categoryPlaceholder[category]}
            </span>
            <Input
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={() => loadParameters()}
              allowClear
            />
          </label>
          {category === "court" && (
            <label>
              <span>法院代码</span>
              <Input
                value={secondaryKeyword}
                onChange={(e) => setSecondaryKeyword(e.target.value)}
                allowClear
              />
            </label>
          )}
          {usesParentCode && (
            <label>
              <span>{category === "cause" ? "上级案由Id" : "上级代码"}</span>
              <Input
                value={secondaryKeyword}
                onChange={(e) => setSecondaryKeyword(e.target.value)}
                allowClear
              />
            </label>
          )}
          <Button type="primary" onClick={() => loadParameters()}>
            查询
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => startParameter()}
          >
            {category === "payment_type"
              ? "新增付款单位"
              : `新增${categoryTitle[category]}`}
          </Button>
        </div>
        <Table
          rowKey="id"
          size="small"
          loading={loading}
          columns={parameterColumns}
          dataSource={visibleParameters}
          locale={{ emptyText: empty }}
          pagination={{
            defaultPageSize: 15,
            showSizeChanger: true,
            pageSizeOptions: ["10", "15", "20", "50", "100", "200"],
            showTotal: (total) => `共 ${total} 条`,
          }}
          scroll={{ x: 1100 }}
        />
      </Card>
    );
  } else if (initialView === "system-parameters-company") {
    const fields: {
      name: string;
      label: string;
      normalize?: typeof sanitizeCompanyDigitsInput;
      type?: "email";
    }[] = [
      { name: "name", label: "公司名称" },
      { name: "code", label: "公司代码" },
      { name: "short_code", label: "公司字母短写代码" },
      { name: "address", label: "公司地址" },
      { name: "phone", label: "联系电话" },
      { name: "fax", label: "联系传真" },
      { name: "email", label: "联系邮箱", type: "email" },
      {
        name: "postal_code",
        label: "联系邮编",
        normalize: sanitizeCompanyDigitsInput,
      },
      { name: "bank_name", label: "开户银行" },
      {
        name: "bank_account",
        label: "开户帐号",
        normalize: sanitizeCompanyDigitsInput,
      },
      { name: "bank_address", label: "开户银行地址" },
    ];
    content = (
      <Card className="panel system-focused" title="公司设置">
        <Alert
          type="info"
          message="请完善以下信息,方便我们更好的为您服务"
          style={{ marginBottom: 16 }}
        />
        <Form
          form={companyForm}
          className="system-config-form"
          labelCol={{ flex: "150px" }}
          wrapperCol={{ flex: "420px" }}
        >
          {fields.map(({ name, label, normalize, type }) => (
            <Form.Item
              key={name}
              name={name}
              label={label}
              normalize={normalize}
              rules={[
                { required: true, message: "请输入红星*必填项." },
                ...(type === "email"
                  ? [{ type, message: "请填写正确联系邮箱！" }]
                  : []),
              ]}
            >
              <Input
                type={type}
                inputMode={normalize ? "numeric" : undefined}
                onInput={normalize ? cleanCompanyDigitsInputEvent : undefined}
              />
            </Form.Item>
          ))}
          <Form.Item label=" ">
            <Button
              type="primary"
              onClick={() => saveConfig("company_profile", companyForm)}
            >
              保存
            </Button>
          </Form.Item>
        </Form>
      </Card>
    );
  } else if (initialView === "system-management-cache") {
    content = (
      <Card className="panel system-focused" title="缓存列表">
        <Table
          rowKey="key"
          size="small"
          rowSelection={{ selectedRowKeys: selectedCacheKeys, onChange: (keys) => setSelectedCacheKeys(keys.map(String)) }}
          title={() => <Popconfirm title="确认批量清空缓存？" onConfirm={clearSelectedCaches}><Button danger>批量清空</Button></Popconfirm>}
          columns={[
            {
              title: "序号",
              key: "no",
              width: 70,
              render: (_v, _r, i) => i + 1,
            },
            { title: "缓存名称", dataIndex: "name" },
            { title: "缓存键值", dataIndex: "key" },
            {
              title: "操作",
              key: "action",
              width: 110,
              render: (_v, row: CacheRow) => (
                <Popconfirm
                  title="确认清空缓存？"
                  onConfirm={() => clearCache(row)}
                >
                  <Button type="link" danger icon={<ClearOutlined />}>
                    清空
                  </Button>
                </Popconfirm>
              ),
            },
          ]}
          dataSource={caches}
          locale={{ emptyText: empty }}
          pagination={{ current: cachePage, pageSize: cachePageSize, total: cacheTotal, showSizeChanger: true, onChange: (page, pageSize) => { setCachePage(page); setCachePageSize(pageSize); void loadCaches(page, pageSize); } }}
        />
      </Card>
    );
  } else if (initialView === "system-management-menu") {
    const systemMenus = menus.filter((row) => row.is_system),
      legacyMenus = menus.filter((row) => !row.is_system);
    const normalizedMenuSearch = menuSearch.trim().toLowerCase();
    const filteredSystemMenus = normalizedMenuSearch
      ? systemMenus.filter((row) => [row.key, row.parent_key, row.label, row.description].join(" ").toLowerCase().includes(normalizedMenuSearch))
      : systemMenus;
    content = (
      <>
        <Card className="panel system-focused" title="菜单列表">
          <Alert
            type="info"
            showIcon
            message="无路由菜单作为目录/权限节点，不会导航到页面；有路由菜单仅允许已实现路由。"
            style={{ marginBottom: 12 }}
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingMenu(null);
              menuForm.resetFields();
              menuForm.setFieldsValue({
                key: "",
                parent_key: "",
                label: "",
                description: "",
                icon: "",
                sort_order: 0,
                is_visible: true,
                is_active: true,
              });
              setMenuOpen(true);
            }}
          >
            新增菜单
          </Button>
          <Space wrap style={{ margin: "12px 0" }}>
            <Input value={menuSearchInput} placeholder="菜单名称/标识" onChange={(event) => setMenuSearchInput(event.target.value)} style={{ width: 220 }} />
            <Button onClick={() => { setMenuSearch(menuSearchInput); setMenuPage(1); }}>查询</Button>
            <Button onClick={() => { setMenuSearchInput(""); setMenuSearch(""); setMenuPage(1); }}>重置</Button>
          </Space>
          <Table
            rowKey="id"
            size="small"
            loading={loading}
            columns={[
              {
                title: "序号",
                key: "no",
                width: 70,
                render: (_v, _r, i) => i + 1,
              },
              { title: "菜单标识", dataIndex: "key", width: 240 },
              {
                title: "父级标识",
                dataIndex: "parent_key",
                width: 220,
                render: (value) => value || "—",
              },
              { title: "菜单名称", dataIndex: "label" },
              { title: "菜单描述", dataIndex: "description" },
              {
                title: "操作",
                key: "action",
                width: 100,
                render: (_v, row: MenuRow) => (
                  <Button
                    type="link"
                    icon={<EditOutlined />}
                    onClick={() => editMenu(row)}
                  >
                    修改
                  </Button>
                ),
              },
            ]}
            dataSource={filteredSystemMenus}
            locale={{ emptyText: empty }}
            pagination={{
              current: menuPage,
              pageSize: menuPageSize,
              total: filteredSystemMenus.length,
              showSizeChanger: true,
              pageSizeOptions: ["10", "15", "20", "30", "50", "100", "200"],
              showQuickJumper: true,
              onChange: (page, size) => { setMenuPage(page); setMenuPageSize(size); },
              showTotal: (total) => `共 ${total} 项`,
            }}
            scroll={{ x: 1100 }}
          />
        </Card>
        {legacyMenus.length > 0 && (
          <Card
            className="panel system-focused"
            title="未纳入当前导航的历史菜单"
            style={{ marginTop: 16 }}
          >
            <Table
              rowKey="id"
              size="small"
              columns={[
                { title: "菜单标识", dataIndex: "key" },
                { title: "菜单名称", dataIndex: "label" },
                { title: "菜单描述", dataIndex: "description" },
                {
                  title: "操作",
                  key: "action",
                  width: 120,
                  render: (_v, row: MenuRow) => (
                    <Popconfirm
                      title="确认删除该历史菜单？"
                      onConfirm={() => removeMenu(row)}
                    >
                      <Button type="link" danger>
                        删除
                      </Button>
                    </Popconfirm>
                  ),
                },
              ]}
              dataSource={legacyMenus}
              pagination={false}
            />
          </Card>
        )}
      </>
    );
  } else if (initialView === "system-management-config") {
    content = (
      <Card className="panel system-focused" title="系统配置">
        <Table
          rowKey="key"
          size="small"
          columns={[
            {
              title: "序号",
              key: "no",
              width: 70,
              render: (_v, _r, i) => i + 1,
            },
            { title: "配置项组", dataIndex: "group", width: 150 },
            { title: "配置项名称", dataIndex: "label", width: 180 },
            { title: "配置项主键", dataIndex: "key", width: 190 },
            {
              title: "键值",
              dataIndex: "value",
              render: (value) => JSON.stringify(value),
            },
          ]}
          dataSource={configs}
          locale={{ emptyText: empty }}
          pagination={{
            defaultPageSize: 15,
            showSizeChanger: true,
            pageSizeOptions: ["10", "15", "20", "50", "100", "200"],
            showQuickJumper: true,
            showTotal: (total) => `共有${total}条`,
          }}
        />
      </Card>
    );
  } else if (initialView === "system-users") {
    content = (
      <>
        <Card className="panel system-focused" title="系统用户管理">
          <div className="system-query">
            <label>
              <span>账号/姓名</span>
              <Input
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onPressEnter={() => loadUsers(keyword)}
                allowClear
              />
            </label>
            <Button type="primary" onClick={() => loadUsers(keyword)}>
              查询
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => editUser()}
            >
              新增账号
            </Button>
          </div>
          <Alert
            type="info"
            showIcon
            message="合同审批人由管理员逐人加入合同审批流程；岗位名称或系统角色不会自动授予审批资格。"
            style={{ marginBottom: 12 }}
          />
          <Table
            rowKey="id"
            size="small"
            loading={loading}
            dataSource={users}
            pagination={{
              pageSize: 20,
              showTotal: (total) => `共 ${total} 个账号`,
            }}
            columns={[
              { title: "登录账号", dataIndex: "username", width: 130 },
              { title: "姓名", dataIndex: "display_name", width: 110 },
              { title: "部门", dataIndex: "department", width: 140 },
              {
                title: "系统角色",
                dataIndex: "role",
                width: 105,
                render: (value) => (
                  <Tag
                    color={
                      value === "admin"
                        ? "red"
                        : value === "manager"
                          ? "blue"
                          : "default"
                    }
                  >
                    {value === "admin"
                      ? "系统管理员"
                      : value === "manager"
                        ? "部门负责人"
                        : value === "auditor"
                          ? "审计人员"
                          : "普通用户"}
                  </Tag>
                ),
              },
              {
                title: "合同审批流程",
                dataIndex: "contract_approval_enabled",
                width: 120,
                render: (value) => (
                  <Tag color={value ? "green" : "default"}>
                    {value ? "已配置" : "未配置"}
                  </Tag>
                ),
              },
              {
                title: "状态",
                dataIndex: "is_active",
                width: 80,
                render: (value) => (
                  <Tag color={value ? "green" : "default"}>
                    {value ? "可用" : "停用"}
                  </Tag>
                ),
              },
              {
                title: "失败次数",
                dataIndex: "failed_login_attempts",
                width: 85,
              },
              {
                title: "锁定至",
                dataIndex: "locked_until",
                width: 165,
                render: formatTime,
              },
              {
                title: "最后登录",
                dataIndex: "last_login_at",
                width: 165,
                render: formatTime,
              },
              {
                title: "操作",
                key: "action",
                width: 250,
                render: (_v, row: SystemUser) => (
                  <Space size={0} wrap>
                    <Button type="link" onClick={() => editUser(row)}>
                      修改
                    </Button>
                    <Button
                      type="link"
                      disabled={row.username === currentUsername}
                      onClick={() => openPasswordReset(row)}
                    >
                      重置密码
                    </Button>
                    <Button
                      type="link"
                      disabled={!row.failed_login_attempts && !row.locked_until}
                      onClick={() => unlockUser(row)}
                    >
                      解锁
                    </Button>
                    {row.role !== "admin" && (
                      <Popconfirm
                        title="确认删除该登录账号？"
                        onConfirm={() => removeUser(row)}
                      >
                        <Button type="link" danger>
                          删除
                        </Button>
                      </Popconfirm>
                    )}
                  </Space>
                ),
              },
            ]}
            scroll={{ x: 1440 }}
          />
        </Card>
        <Modal
          open={userOpen}
          title={editingUser ? "修改系统账号" : "新增系统账号"}
          okText="保存"
          cancelText="取消"
          onOk={saveUser}
          onCancel={() => setUserOpen(false)}
          destroyOnHidden
          width={680}
        >
          <Form form={userForm} layout="vertical">
            <div className="system-modal-grid">
              {!editingUser && (
                <Form.Item
                  label="登录账号"
                  name="username"
                  rules={[{ required: true }, { min: 3 }]}
                >
                  <Input />
                </Form.Item>
              )}
              <Form.Item
                label="姓名"
                name="display_name"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                label="部门"
                name="department"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                label={
                  editingUser
                    ? "新密码（留空不修改；填写后用户须首次改密）"
                    : "一次性初始密码"
                }
                name="password"
                rules={editingUser ? [] : [{ required: true }, { min: 8 }]}
              >
                <Input.Password />
              </Form.Item>
              <Form.Item
                label="系统角色"
                name="role"
                rules={[{ required: true }]}
              >
                <Select
                  options={[
                    { value: "admin", label: "系统管理员（最高权限）" },
                    { value: "manager", label: "部门负责人" },
                    { value: "auditor", label: "审计人员" },
                    { value: "user", label: "普通用户" },
                  ]}
                />
              </Form.Item>
              <Form.Item
                label="是否可用"
                name="is_active"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
              <Form.Item
                label="合同审批流程人员"
                name={["profile", "contract_approval_enabled"]}
                valuePropName="checked"
              >
                <Switch checkedChildren="是" unCheckedChildren="否" />
              </Form.Item>
              <Form.Item label="Email" name={["profile", "email"]}>
                <Input />
              </Form.Item>
              <Form.Item label="手机" name={["profile", "mobile"]}>
                <Input />
              </Form.Item>
              <Form.Item label="办公电话" name={["profile", "office_phone"]}>
                <Input />
              </Form.Item>
            </div>
          </Form>
        </Modal>
        <Modal
          open={Boolean(resettingUser)}
          title={`重置密码：${resettingUser?.username || ""}`}
          okText="确认重置"
          cancelText="取消"
          onOk={resetPassword}
          onCancel={() => {
            setResettingUser(null);
            resetPasswordForm.resetFields();
          }}
          destroyOnHidden
        >
          <Alert
            type="warning"
            showIcon
            message="重置后将解除登录锁定，且该账号下次登录必须修改密码。"
            style={{ marginBottom: 16 }}
          />
          <Form form={resetPasswordForm} layout="vertical">
            <Form.Item
              label="临时新密码"
              name="new_password"
              rules={[
                { required: true, message: "请输入临时新密码" },
                { min: 8, message: "密码至少 8 位" },
              ]}
            >
              <Input.Password autoComplete="new-password" />
            </Form.Item>
            <Form.Item
              label="确认临时新密码"
              name="confirm_password"
              dependencies={["new_password"]}
              rules={[
                { required: true, message: "请再次输入临时新密码" },
                {
                  validator: (_rule, value) =>
                    !value ||
                    value === resetPasswordForm.getFieldValue("new_password")
                      ? Promise.resolve()
                      : Promise.reject(new Error("两次密码输入不一致")),
                },
              ]}
            >
              <Input.Password autoComplete="new-password" />
            </Form.Item>
          </Form>
        </Modal>
      </>
    );
  } else if (initialView === "system-roles") {
    content = (
      <>
        <Card className="panel system-focused" title="系统角色权限">
          <Alert
            type="warning"
            showIcon
            message="系统管理员为最高权限，必须保留全部菜单、全部字段和全所数据范围。"
            style={{ marginBottom: 12 }}
          />
          <Table
            rowKey="role"
            size="small"
            loading={loading}
            dataSource={rolePermissions}
            pagination={false}
            columns={[
              { title: "角色", dataIndex: "display_name", width: 140 },
              { title: "角色代码", dataIndex: "role", width: 110 },
              { title: "数据范围", dataIndex: "data_scope", width: 130 },
              {
                title: "菜单权限",
                dataIndex: "menu_keys",
                render: (value: string[]) => `${value.length} 项`,
              },
              {
                title: "字段权限",
                dataIndex: "field_keys",
                width: 110,
                render: (value: string[]) => `${value.length} 项`,
              },
              {
                title: "更新时间",
                dataIndex: "updated_at",
                width: 165,
                render: formatTime,
              },
              {
                title: "操作",
                key: "action",
                width: 90,
                render: (_v, row: RolePermission) => (
                  <Button type="link" onClick={() => editRole(row)}>
                    配置
                  </Button>
                ),
              },
            ]}
          />
        </Card>
        <Modal
          open={roleOpen}
          title={`配置角色：${editingRole?.display_name || ""}`}
          okText="保存权限"
          cancelText="取消"
          onOk={saveRole}
          onCancel={() => setRoleOpen(false)}
          okButtonProps={{ disabled: editingRole?.role === "admin" }}
          destroyOnHidden
          width={760}
        >
          <Form
            form={roleForm}
            layout="vertical"
            disabled={editingRole?.role === "admin"}
          >
            <Form.Item
              name="data_scope"
              label="数据范围"
              rules={[{ required: true }]}
            >
              <Select
                options={[
                  { value: "全所数据", label: "全所数据" },
                  { value: "本部门数据", label: "本部门数据" },
                  { value: "授权审批数据", label: "授权审批数据" },
                  { value: "本人及共享数据", label: "本人及共享数据" },
                ]}
              />
            </Form.Item>
            <Form.Item
              name="menu_keys"
              label="菜单权限"
              rules={[{ required: true }]}
            >
              <TreeSelect
                treeData={menuTreeData}
                treeCheckable
                treeDefaultExpandAll
                  showCheckedStrategy={TreeSelect.SHOW_ALL}
                disabled={editingRole?.role === "admin"}
              />
            </Form.Item>
            <Form.Item
              name="field_keys"
              label="字段权限"
              rules={[{ required: true }]}
            >
              <Select
                mode="multiple"
                options={availableFieldKeys.map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
            {editingRole?.role === "admin" && (
              <Alert
                type="info"
                showIcon
                message="系统管理员权限由系统锁定为全部权限，不允许降权。"
              />
            )}
          </Form>
        </Modal>
      </>
    );
  } else if (initialView === "system-security") {
    content = (
      <Card
        className="panel system-focused"
        title="账号安全策略"
        loading={loading}
      >
        <Form
          form={securityForm}
          className="system-config-form"
          labelCol={{ flex: "180px" }}
          wrapperCol={{ flex: "260px" }}
        >
          <Form.Item
            name="min_password_length"
            label="密码最小长度"
            rules={[{ required: true }]}
          >
            <InputNumber min={8} max={128} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="max_failed_attempts"
            label="最大连续失败次数"
            rules={[{ required: true }]}
          >
            <InputNumber min={1} max={20} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="lock_minutes"
            label="账号锁定时间"
            rules={[{ required: true }]}
          >
            <InputNumber
              min={1}
              max={1440}
              addonAfter="分钟"
              style={{ width: "100%" }}
            />
          </Form.Item>
          <Form.Item
            name="token_minutes"
            label="登录有效期"
            rules={[{ required: true }]}
          >
            <InputNumber
              min={5}
              max={10080}
              addonAfter="分钟"
              style={{ width: "100%" }}
            />
          </Form.Item>
          <Form.Item label="最近修改">
            {securityPolicy
              ? `${securityPolicy.updated_by || "—"}｜${formatTime(securityPolicy.updated_at)}`
              : "—"}
          </Form.Item>
          <Form.Item label=" ">
            <Button type="primary" onClick={saveSecurity}>
              保存安全策略
            </Button>
          </Form.Item>
        </Form>
      </Card>
    );
  } else {
    content = (
      <Card className="panel system-focused" title="客户共享时间设置">
        <Form
          form={shareForm}
          className="share-config-form"
          labelCol={{ flex: "150px" }}
          wrapperCol={{ flex: "220px" }}
        >
          {[
            ["all_days", "全部客户"],
            ["filed_days", "立案客户"],
            ["premium_days", "高级客户"],
            ["standard_days", "中级客户"],
            ["basic_days", "初级客户"],
            ["shared_days", "共享客户"],
          ].map(([name, label]) => (
            <Form.Item
              key={name}
              name={name}
              label={label}
              normalize={sanitizeShareDaysInput}
              rules={[
                { required: true },
                {
                  validator: (_rule, value) =>
                    isShareDaysValueValid(value)
                      ? Promise.resolve()
                      : Promise.reject(
                          new Error("请输入 1–3650 之间的天数"),
                        ),
                },
              ]}
            >
              <Input
                inputMode="numeric"
                maxLength={4}
                onInput={cleanShareDaysInputEvent}
                addonAfter="天"
              />
            </Form.Item>
          ))}
          <Form.Item label=" ">
            <Button
              type="primary"
              onClick={() => saveConfig("customer_share_policy", shareForm)}
            >
              保存
            </Button>
          </Form.Item>
        </Form>
      </Card>
    );
  }

  return (
    <>
      {content}
      <Modal
        open={parameterOpen}
        title={`${editingParameter ? "修改" : "新增"}${categoryTitle[category] || "参数"}`}
        okText="保存"
        cancelText="取消"
        onOk={saveParameter}
        onCancel={() => setParameterOpen(false)}
        destroyOnHidden
      >
        <Form form={parameterForm} layout="vertical">
          <div className="system-modal-grid">
            <Form.Item label="代码" name="code" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item label="名称" name="name" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            {(extraFields[category] || []).map((item) => (
              <Form.Item key={item.key} label={item.label} name={item.key}>
                <Input />
              </Form.Item>
            ))}
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
              <Switch checkedChildren="是" unCheckedChildren="否" />
            </Form.Item>
          </div>
        </Form>
      </Modal>
      <Modal
        open={menuOpen}
        title={editingMenu ? "修改菜单" : "新增菜单"}
        okText="保存"
        cancelText="取消"
        onOk={saveMenu}
        onCancel={() => setMenuOpen(false)}
        destroyOnHidden
      >
        <Form form={menuForm} layout="vertical">
          <Form.Item label="菜单标识">
            <Input value={editingMenu?.key || ""} disabled />
          </Form.Item>
          <Form.Item label="父级标识">
            <Input value={editingMenu?.parent_key || "顶级菜单"} disabled />
          </Form.Item>
          <Form.Item label="菜单名称" name="label" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="菜单描述" name="description">
            <Input />
          </Form.Item>
          <Form.Item label="图标" name="icon">
            <Input placeholder="可选" />
          </Form.Item>
          <Form.Item
            label="排序号"
            name="sort_order"
            rules={[{ required: true }]}
          >
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="是否显示" name="is_visible" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item label="是否可用" name="is_active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
