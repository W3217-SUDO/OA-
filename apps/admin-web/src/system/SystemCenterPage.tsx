import { useEffect, useMemo, useState } from "react";
import { Form, message } from "antd";
import { api } from "../api";
import "../system-center.css";
import {
  categoryByRoute,
  parameterRelationConfigs,
  relationTargetIds,
  isCaseFileTypeParentValid,
  feeTypeParentOptions,
} from "./constants";
import type {
  ParameterRow,
  ParameterRelationKind,
  ParameterRelationEditor,
  SystemConfig,
  CacheRow,
  CacheSummary,
  MenuRow,
  SystemUser,
  RolePermission,
  SecurityPolicy,
} from "./types";
import { SystemParameterManagement } from "./SystemParameterManagement";
import { SystemCacheManagement } from "./SystemCacheManagement";
import { SystemMenuManagement } from "./SystemMenuManagement";
import { SystemConfigList } from "./SystemConfigList";
import { SystemUserManagement } from "./SystemUserManagement";
import { SystemPermissionManagement } from "./SystemPermissionManagement";
import { SystemSecurityPolicy } from "./SystemSecurityPolicy";
import { SystemCompanySettings } from "./SystemCompanySettings";
import { SystemShareSettings } from "./SystemShareSettings";

export default function SystemCenterPage({
  initialView = "system-parameters",
}: {
  initialView?: string;
}) {
  const category = categoryByRoute[initialView] || "";
  const numericCode = category === "fee_type" || category === "case_phase";
  const [parameters, setParameters] = useState<ParameterRow[]>([]);
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [caches, setCaches] = useState<CacheRow[]>([]);
  const [cacheSummary, setCacheSummary] = useState<CacheSummary | null>(null);
  const [cacheActionPending, setCacheActionPending] = useState(false);
  const [cacheTotal, setCacheTotal] = useState(0);
  const [cachePage, setCachePage] = useState(1);
  const [cachePageSize, setCachePageSize] = useState(15);
  const [cacheJumpPage, setCacheJumpPage] = useState("");
  const [selectedCacheKeys, setSelectedCacheKeys] = useState<string[]>([]);
  const [menus, setMenus] = useState<MenuRow[]>([]);
  const [menuPage, setMenuPage] = useState(1);
  const [menuPageSize, setMenuPageSize] = useState(15);
  const [menuJumpPage, setMenuJumpPage] = useState("");
  const [menuSearchInput, setMenuSearchInput] = useState("");
  const [menuSearch, setMenuSearch] = useState("");
  const [users, setUsers] = useState<SystemUser[]>([]);
  const [userDepartmentOptions, setUserDepartmentOptions] = useState<
    { value: string; label: string }[]
  >([]);
  const [rolePermissions, setRolePermissions] = useState<RolePermission[]>([]);
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
  const [relationEditor, setRelationEditor] =
    useState<ParameterRelationEditor | null>(null);
  const [relationTargetOptions, setRelationTargetOptions] = useState<
    { value: number; label: string; disabled?: boolean }[]
  >([]);
  const [selectedRelationTargetIds, setSelectedRelationTargetIds] = useState<
    number[]
  >([]);
  const [relationSaving, setRelationSaving] = useState(false);
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
      const { data } = await api.get("/system/cache", { params: { page, page_size: pageSize } });
      setCaches(data.items);
      setCacheTotal(data.total ?? data.items.length);
      setCacheSummary(data.summary ?? null);
      setCachePage(page);
      setCachePageSize(pageSize);
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
  const loadUserDepartments = async () => {
    try {
      const { data } = await api.get("/hr/departments", {
        params: { active_only: true },
      });
      setUserDepartmentOptions(
        (data.items || []).map((item: { name: string }) => ({
          value: item.name,
          label: item.name,
        })),
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "部门选项加载失败");
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
    ) {
      void loadConfigs();
    }
    else if (initialView === "system-management-cache") void loadCaches();
    else if (initialView === "system-management-menu") void loadMenus();
    else if (initialView === "system-users") {
      void loadUsers();
      void loadUserDepartments();
    }
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
            nature: category === "payment_type" ? "官费" : undefined,
            case_kinds: ["专利", "商标"],
            allow_repeat: true,
          },
    );
    setParameterOpen(true);
  };
  const saveParameter = async () => {
    const value = await parameterForm.validateFields();
    if (
      category === "case_file_type" &&
      !isCaseFileTypeParentValid(value.parent_code, parameters, editingParameter?.id)
    ) {
      parameterForm.setFields([
        {
          name: "parent_code",
          errors: ["请选择有效的上级文件类型，且不能选择自身"],
        },
      ]);
      return;
    }
    if (
      category === "fee_type" &&
      value.parent_code &&
      !feeTypeParentOptions(parameters, editingParameter?.id).some(
        (option) => option.value === value.parent_code,
      )
    ) {
      parameterForm.setFields([{ name: "parent_code", errors: ["请选择有效的上级费用类型，且不能选择自身或下级"] }]);
      return;
    }
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
            (extraFieldsLocal[category] || []).map((item) => [
              item.key,
              value[item.key] || "",
            ]),
          );
    const paymentUnit = category === "payment_type";
    const payload = {
      category,
      code: paymentUnit
        ? editingParameter?.code || `PAYEE-${Date.now()}`
        : value.code,
      name: paymentUnit ? value.nature : value.name,
      sort_order: paymentUnit
        ? editingParameter?.sort_order || parameters.length + 1
        : value.sort_order,
      is_active: paymentUnit
        ? editingParameter?.is_active !== false
        : value.is_active,
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
      message.success("保存成功！");
      setParameterOpen(false);
      void loadParameters("");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "保存失败！");
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
  const openParameterRelation = async (
    kind: ParameterRelationKind,
    source: ParameterRow,
  ) => {
    const config = parameterRelationConfigs[kind];
    try {
      const [targetsResult, relationResult] = await Promise.all([
        api.get("/system/parameters", {
          params: { category: config.targetCategory },
        }),
        api.get(`/system/parameter-relations/${kind}`, {
          params: { source_id: source.id },
        }),
      ]);
      const targetIds = relationTargetIds(relationResult.data, source.id);
      const targetIdSet = new Set(targetIds);
      const targets = (targetsResult.data.items as ParameterRow[])
        .filter((row) => row.is_active || targetIdSet.has(row.id))
        .sort(
          (left, right) =>
            left.sort_order - right.sort_order ||
            left.code.localeCompare(right.code),
        )
        .map((row) => ({
          value: row.id,
          label: `${row.name}（${row.code}）${row.is_active ? "" : "（已停用）"}`,
          disabled: !row.is_active,
        }));
      setRelationTargetOptions(targets);
      setSelectedRelationTargetIds(targetIds);
      setRelationEditor({ ...config, source });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || `${config.title}加载失败`);
    }
  };
  const saveParameterRelation = async () => {
    if (!relationEditor) return;
    setRelationSaving(true);
    try {
      await api.put(`/system/parameter-relations/${relationEditor.kind}`, {
        source_id: relationEditor.source.id,
        target_ids: selectedRelationTargetIds,
      });
      message.success(`${relationEditor.title}已保存`);
      setRelationEditor(null);
      setRelationTargetOptions([]);
      setSelectedRelationTargetIds([]);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || `${relationEditor.title}保存失败`);
    } finally {
      setRelationSaving(false);
    }
  };
  const closeRelationEditor = () => {
    setRelationEditor(null);
    setRelationTargetOptions([]);
    setSelectedRelationTargetIds([]);
  };
  const clearCache = async (row: CacheRow) => {
    if (cacheActionPending) return;
    setCacheActionPending(true);
    try {
      await api.post(`/system/cache/${row.key}/clear`);
      message.success("缓存已清空");
      setSelectedCacheKeys((keys) => keys.filter((key) => key !== row.key));
      void loadCaches(cachePage, cachePageSize);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "清理失败");
    } finally {
      setCacheActionPending(false);
    }
  };
  const clearSelectedCaches = async () => {
    if (!selectedCacheKeys.length) {
      message.info("请先选择要清除的缓存");
      return;
    }
    if (cacheActionPending) return;
    setCacheActionPending(true);
    try {
      await api.post("/system/caches/clear", { cache_keys: selectedCacheKeys });
      message.success(`已清除 ${selectedCacheKeys.length} 项缓存`);
      setSelectedCacheKeys([]);
      void loadCaches(cachePage, cachePageSize);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "批量清除缓存失败");
    } finally {
      setCacheActionPending(false);
    }
  };
  const clearAllCaches = async () => {
    if (cacheActionPending) return;
    setCacheActionPending(true);
    try {
      await api.post("/system/cache/clear-all");
      message.success("当前进程缓存已清除");
      setSelectedCacheKeys([]);
      void loadCaches(cachePage, cachePageSize);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "清除全部缓存失败");
    } finally {
      setCacheActionPending(false);
    }
  };
  const jumpToCachePage = () => {
    const requested = Number(cacheJumpPage);
    if (!Number.isInteger(requested)) return;
    const maxPage = Math.max(1, Math.ceil(cacheTotal / cachePageSize));
    const target = Math.min(maxPage, Math.max(1, requested));
    setCachePage(target);
    setCacheJumpPage("");
    void loadCaches(target, cachePageSize);
  };
  const editMenu = (row: MenuRow) => {
    setEditingMenu(row);
    menuForm.resetFields();
    menuForm.setFieldsValue(row);
    setMenuOpen(true);
  };
  const newMenu = () => {
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
  };
  const jumpToMenuPage = () => {
    const requested = Number(menuJumpPage);
    if (!Number.isInteger(requested)) return;
    const normalized = menuSearch.trim().toLowerCase();
    const total = menus.filter((row) => {
      if (!row.is_system) return false;
      if (!normalized) return true;
      return [row.key, row.parent_key, row.label, row.description]
        .join(" ")
        .toLowerCase()
        .includes(normalized);
    }).length;
    const maxPage = Math.max(1, Math.ceil(total / menuPageSize));
    setMenuPage(Math.min(maxPage, Math.max(1, requested)));
    setMenuJumpPage("");
  };
  const saveMenu = async () => {
    const value = await menuForm.validateFields();
    try {
      const { data } = editingMenu
        ? await api.patch(`/system/menus/${editingMenu.id}`, value)
        : await api.post("/system/menus", value);
      message.success("保存成功.");
      setMenuOpen(false);
      window.dispatchEvent(new Event("sunhold:menus-updated"));
      setMenus((items) =>
        editingMenu
          ? items.map((item) => (item.id === data.id ? data : item))
          : [...items, data],
      );
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "保存失败！");
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
            role_ids: row.role_ids?.length ? row.role_ids : [row.role],
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
            role_ids: ["user"],
            is_active: true,
            profile: { contract_approval_enabled: false },
          },
    );
    setUserOpen(true);
  };
  const saveUser = async () => {
    const value = await userForm.validateFields();
    const roleIds = Array.from(
      new Set(
        (
          Array.isArray(value.role_ids) && value.role_ids.length
            ? value.role_ids
            : value.role
              ? [value.role]
              : ["user"]
        ).filter(Boolean),
      ),
    );
    const payload = {
      ...value,
      role: roleIds.includes("admin") ? "admin" : roleIds[0],
      role_ids: roleIds,
      profile: value.profile || {},
    };
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
    if (row.role === "admin" || row.role_ids?.includes("admin")) {
      message.error("系统管理员账号不可删除");
      return;
    }
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
  const closeResetPassword = () => {
    setResettingUser(null);
    resetPasswordForm.resetFields();
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
    if (editingRole.role === "admin") {
      message.error("系统管理员权限不可修改");
      return;
    }
    const value = await roleForm.validateFields();
    try {
      await api.patch(`/system/role-permissions/${editingRole.role}`, value);
      message.success("保存成功！");
      setRoleOpen(false);
      void loadRoles();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "保存失败！");
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

  // 本地引用 extraFields，避免循环依赖
  const extraFieldsLocal: Record<string, { key: string; label: string }[]> = {
    case_type: [{ key: "letter_code", label: "类型字母名称" }],
    fee_type: [{ key: "parent_code", label: "上级费用类型" }],
    case_phase: [
      { key: "parent_code", label: "上级阶段Id" },
      { key: "case_type", label: "案件类型" },
    ],
    notary_office: [{ key: "number_template", label: "公证号模板" }],
    cause: [{ key: "parent_code", label: "上级案由Id" }],
    payment_type: [
      { key: "nature", label: "付款性质" },
      { key: "payee", label: "收款单位" },
      { key: "account_bank", label: "开户行" },
      { key: "account", label: "账号信息" },
    ],
    case_file_type: [{ key: "parent_code", label: "上级文件类型代码" }],
    district: [{ key: "parent_code", label: "上级地区代码" }],
    court_officer: [
      { key: "court_code", label: "法院代码" },
      { key: "role", label: "职务" },
      { key: "phone", label: "联系电话" },
    ],
  };

  let content: React.ReactNode;
  if (category) {
    content = (
      <SystemParameterManagement
        category={category}
        numericCode={numericCode}
        parameters={parameters}
        keyword={keyword}
        secondaryKeyword={secondaryKeyword}
        loading={loading}
        parameterOpen={parameterOpen}
        editingParameter={editingParameter}
        relationEditor={relationEditor}
        relationTargetOptions={relationTargetOptions}
        selectedRelationTargetIds={selectedRelationTargetIds}
        relationSaving={relationSaving}
        parameterForm={parameterForm}
        onKeywordChange={setKeyword}
        onSecondaryKeywordChange={setSecondaryKeyword}
        onLoadParameters={loadParameters}
        onStartParameter={startParameter}
        onSaveParameter={saveParameter}
        onRemoveParameter={removeParameter}
        onParameterOpenChange={setParameterOpen}
        onOpenParameterRelation={openParameterRelation}
        onSaveParameterRelation={saveParameterRelation}
        onRelationEditorClose={closeRelationEditor}
        onSelectedRelationTargetIdsChange={setSelectedRelationTargetIds}
      />
    );
  } else if (initialView === "system-parameters-company") {
    content = (
      <SystemCompanySettings
        companyForm={companyForm}
        onSaveCompany={() => saveConfig("company_profile", companyForm)}
      />
    );
  } else if (initialView === "system-management-cache") {
    content = (
      <SystemCacheManagement
        caches={caches}
        cacheSummary={cacheSummary}
        cacheActionPending={cacheActionPending}
        cacheTotal={cacheTotal}
        cachePage={cachePage}
        cachePageSize={cachePageSize}
        cacheJumpPage={cacheJumpPage}
        selectedCacheKeys={selectedCacheKeys}
        onSelectedCacheKeysChange={setSelectedCacheKeys}
        onCacheJumpPageChange={setCacheJumpPage}
        onLoadCaches={loadCaches}
        onClearCache={clearCache}
        onClearSelectedCaches={clearSelectedCaches}
        onClearAllCaches={clearAllCaches}
        onJumpToCachePage={jumpToCachePage}
      />
    );
  } else if (initialView === "system-management-menu") {
    content = (
      <SystemMenuManagement
        menus={menus}
        menuPage={menuPage}
        menuPageSize={menuPageSize}
        menuJumpPage={menuJumpPage}
        menuSearchInput={menuSearchInput}
        menuSearch={menuSearch}
        menuOpen={menuOpen}
        editingMenu={editingMenu}
        loading={loading}
        menuForm={menuForm}
        onMenuSearchInputChange={setMenuSearchInput}
        onMenuSearch={(value) => { setMenuSearch(value); setMenuPage(1); }}
        onMenuPageChange={(page, size) => { setMenuPage(page); setMenuPageSize(size); }}
        onMenuJumpPageChange={setMenuJumpPage}
        onJumpToMenuPage={jumpToMenuPage}
        onEditMenu={editMenu}
        onSaveMenu={saveMenu}
        onRemoveMenu={removeMenu}
        onMenuOpenChange={setMenuOpen}
        onNewMenu={newMenu}
        onResetMenuSearch={() => { setMenuSearchInput(""); setMenuSearch(""); setMenuPage(1); }}
      />
    );
  } else if (initialView === "system-management-config") {
    content = <SystemConfigList configs={configs} />;
  } else if (initialView === "system-users") {
    content = (
      <SystemUserManagement
        users={users}
        keyword={keyword}
        loading={loading}
        userOpen={userOpen}
        editingUser={editingUser}
        resettingUser={resettingUser}
        userDepartmentOptions={userDepartmentOptions}
        userForm={userForm}
        resetPasswordForm={resetPasswordForm}
        onKeywordChange={setKeyword}
        onLoadUsers={loadUsers}
        onEditUser={editUser}
        onSaveUser={saveUser}
        onRemoveUser={removeUser}
        onUserOpenChange={setUserOpen}
        onOpenPasswordReset={openPasswordReset}
        onResetPassword={resetPassword}
        onResetPasswordClose={closeResetPassword}
        onUnlockUser={unlockUser}
      />
    );
  } else if (initialView === "system-roles") {
    content = (
      <SystemPermissionManagement
        rolePermissions={rolePermissions}
        availableFieldKeys={availableFieldKeys}
        menus={menus}
        roleOpen={roleOpen}
        editingRole={editingRole}
        loading={loading}
        roleForm={roleForm}
        onEditRole={editRole}
        onSaveRole={saveRole}
        onRoleOpenChange={setRoleOpen}
      />
    );
  } else if (initialView === "system-security") {
    content = (
      <SystemSecurityPolicy
        securityPolicy={securityPolicy}
        loading={loading}
        securityForm={securityForm}
        onSaveSecurity={saveSecurity}
      />
    );
  } else {
    content = (
      <SystemShareSettings
        shareForm={shareForm}
        onSaveShare={() => saveConfig("customer_share_policy", shareForm)}
      />
    );
  }

  return <>{content}</>;
}
