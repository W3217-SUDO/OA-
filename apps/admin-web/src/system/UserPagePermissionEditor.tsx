import { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Button, Modal, Popconfirm, Space, Spin, Tag, Tree, message } from "antd";
import { api } from "../api";
import { normalizeWorkspaceRoute, notifyPermissionsUpdated } from "../workspacePermissions";
import { buildMenuTreeData } from "./SystemMenuManagement";
import type { MenuRow, SystemUser } from "./types";

type UserPagePermissionTarget = {
  username: string;
  displayName: string;
  userId?: number;
};

type UserPagePermissions = {
  user_id: number;
  username: string;
  overrides: Record<string, unknown>;
  effective: { menu_keys: string[] };
};

type PagePermissionNode = ReturnType<typeof buildMenuTreeData>[number];
const BASE_MENU_KEYS = ["dashboard", "user-center"];

function menuTreeKeys(nodes: PagePermissionNode[]): string[] {
  return nodes.flatMap((node) => [String(node.key), ...menuTreeKeys(node.children || [])]);
}

function menuBranchKeys(nodes: PagePermissionNode[], target: string): string[] {
  for (const node of nodes) {
    if (node.key === target) return menuTreeKeys([node]);
    const found = menuBranchKeys(node.children || [], target);
    if (found.length) return found;
  }
  return [];
}

function menuAncestorKeys(nodes: PagePermissionNode[], target: string, ancestors: string[] = []): string[] {
  for (const node of nodes) {
    if (node.key === target) return ancestors;
    const found = menuAncestorKeys(node.children || [], target, [...ancestors, String(node.key)]);
    if (found.length) return found;
  }
  return [];
}

function protectBasePages(nodes: PagePermissionNode[], inherited = false): PagePermissionNode[] {
  return nodes.map((node) => {
    const protectedPage = inherited || BASE_MENU_KEYS.includes(String(node.key));
    return { ...node, disableCheckbox: protectedPage, children: protectBasePages(node.children || [], protectedPage) };
  });
}

function basePageKeys(nodes: PagePermissionNode[]): string[] {
  return Array.from(new Set([...BASE_MENU_KEYS, ...menuBranchKeys(nodes, "user-center")]));
}

function effectiveSelectedPageKeys(keys: string[], nodes: PagePermissionNode[]): string[] {
  const effectiveRoutes = new Set(keys.map(normalizeWorkspaceRoute));
  return Array.from(new Set([
    ...menuTreeKeys(nodes).filter((key) => effectiveRoutes.has(normalizeWorkspaceRoute(key))),
    ...basePageKeys(nodes),
  ]));
}

function selectedPagePermissionKeys(keys: string[], nodes: PagePermissionNode[]): string[] {
  const treeKeys = new Set(menuTreeKeys(nodes));
  return Array.from(new Set([...keys.filter((key) => treeKeys.has(key)), ...basePageKeys(nodes)]));
}

function halfSelectedMenuKeys(nodes: PagePermissionNode[], selected: ReadonlySet<string>): string[] {
  const halfSelected: string[] = [];
  const visit = (node: PagePermissionNode): boolean => {
    const childrenSelected = (node.children || []).map(visit).some(Boolean);
    if (childrenSelected && !selected.has(String(node.key))) halfSelected.push(String(node.key));
    return selected.has(String(node.key)) || childrenSelected;
  };
  nodes.forEach(visit);
  return halfSelected;
}

function validatePermissionResponse(data: UserPagePermissions, userId: number) {
  if (data.user_id !== userId || !Array.isArray(data.effective?.menu_keys) || !data.overrides) {
    throw new Error("用户页面权限返回不完整，请重新加载");
  }
}

export function UserPagePermissionEditor({
  target,
  onClose,
}: {
  target: UserPagePermissionTarget | null;
  onClose: () => void;
}) {
  const [snapshot, setSnapshot] = useState<UserPagePermissions | null>(null);
  const [menuRows, setMenuRows] = useState<MenuRow[]>([]);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const requestController = useRef<AbortController | null>(null);
  const menuTree = useMemo(
    () => protectBasePages(buildMenuTreeData(menuRows.filter((item) => item.is_active))),
    [menuRows],
  );
  const protectedKeys = useMemo(() => basePageKeys(menuTree), [menuTree]);
  const halfSelectedKeys = useMemo(() => halfSelectedMenuKeys(menuTree, new Set(selectedKeys)), [menuTree, selectedKeys]);

  useEffect(() => {
    requestController.current?.abort();
    setSnapshot(null);
    setSelectedKeys([]);
    setMenuRows([]);
    setError("");
    setSaving(false);
    if (!target) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    requestController.current = controller;
    setLoading(true);
    const load = async () => {
      try {
        let userId = target.userId;
        if (!Number.isInteger(userId) || Number(userId) <= 0) {
          // 员工详情使用已经保存的账号关联键，不用姓名推断登录账号。
          const username = target.username.trim();
          if (!username) throw new Error("员工尚未关联登录账号，请先维护账号资料");
          const { data } = await api.get<{ items: SystemUser[] }>("/system/users", {
            params: { keyword: username },
            signal: controller.signal,
          });
          const accounts = data.items.filter((item) => item.username.trim().toLowerCase() === username.toLowerCase());
          if (accounts.length !== 1) {
            throw new Error(accounts.length ? "员工关联账号不唯一，请先维护账号资料" : "员工关联登录账号不存在，请先维护账号资料");
          }
          userId = accounts[0].id;
        }
        const resolvedUserId = Number(userId);
        const [permissionResponse, menuResponse] = await Promise.all([
          api.get<UserPagePermissions>(`/system/users/${resolvedUserId}/permissions`, { signal: controller.signal }),
          api.get<{ items: MenuRow[] }>("/system/menus", { signal: controller.signal }),
        ]);
        if (controller.signal.aborted) return;
        validatePermissionResponse(permissionResponse.data, resolvedUserId);
        if (!Array.isArray(menuResponse.data.items)) throw new Error("页面目录返回不完整，请重新加载");
        setSnapshot(permissionResponse.data);
        setMenuRows(menuResponse.data.items);
        const nextMenuTree = buildMenuTreeData(menuResponse.data.items.filter((item) => item.is_active));
        setSelectedKeys(effectiveSelectedPageKeys(permissionResponse.data.effective.menu_keys, nextMenuTree));
      } catch (failure: any) {
        if (!controller.signal.aborted) {
          setError(failure?.response?.data?.detail || failure?.message || "用户页面权限加载失败");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    void load();
    return () => requestController.current?.abort();
  }, [target, reloadKey]);

  const save = async (inherit: boolean) => {
    if (!snapshot || loading || saving) return;
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setSaving(true);
    setError("");
    try {
      // 只提交页面覆盖；字段权限和数据范围由接口保留，恢复继承也只清除页面覆盖。
      const payload = inherit
        ? { clear_menu_keys: true }
        : { menu_keys: selectedPagePermissionKeys(selectedKeys, menuTree) };
      const { data } = await api.patch<UserPagePermissions>(
        `/system/users/${snapshot.user_id}/permissions`,
        payload,
        { signal: controller.signal },
      );
      if (controller.signal.aborted) return;
      validatePermissionResponse(data, snapshot.user_id);
      setSnapshot(data);
      setSelectedKeys(effectiveSelectedPageKeys(data.effective.menu_keys, menuTree));
      notifyPermissionsUpdated();
      message.success(inherit ? "已恢复岗位/角色页面授权" : "用户页面授权已保存");
    } catch (failure: any) {
      if (!controller.signal.aborted) {
        setError(failure?.response?.data?.detail || failure?.message || "用户页面授权保存失败");
      }
    } finally {
      if (!controller.signal.aborted) setSaving(false);
    }
  };

  const independentlyConfigured = Boolean(snapshot && Object.hasOwn(snapshot.overrides, "menu_keys"));
  return (
    <Modal
      open={Boolean(target)}
      title={`页面授权：${target?.displayName || ""}`}
      width={760}
      onCancel={onClose}
      destroyOnHidden
      footer={(
        <Space>
          <Button onClick={onClose}>关闭</Button>
          <Popconfirm
            title="恢复岗位/角色页面授权？"
            description="用户独立页面授权将被清除，改为采用岗位/角色的页面授权。"
            onConfirm={() => save(true)}
            okText="恢复继承"
            cancelText="取消"
            disabled={!independentlyConfigured || loading || saving}
          >
            <Button disabled={!independentlyConfigured || loading || saving}>恢复岗位/角色页面授权</Button>
          </Popconfirm>
          <Button type="primary" loading={saving} disabled={!snapshot || loading} onClick={() => void save(false)}>
            保存页面授权
          </Button>
        </Space>
      )}
    >
      <Alert
        type="info"
        showIcon
        title="勾选的页面对该用户开放，未勾选的页面隐藏。"
        description="用户独立授权优先于岗位/角色授权。勾选目录会选择全部子页，可单独取消子页。控制台和用户中心为基础页面，必须保留。"
        style={{ marginBottom: 16 }}
      />
      {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 16 }} />}
      <Spin spinning={loading}>
        {snapshot && (
          <>
            <Space style={{ marginBottom: 12 }}>
              <span>登录账号：{snapshot.username}</span>
              <Tag>{independentlyConfigured ? "用户独立页面授权" : "继承岗位/角色页面授权"}</Tag>
            </Space>
            <div style={{ maxHeight: "55vh", overflow: "auto" }}>
              <Tree
                checkable
                checkStrictly
                defaultExpandAll
                treeData={menuTree}
                checkedKeys={{ checked: selectedKeys, halfChecked: halfSelectedKeys }}
                disabled={saving}
                onCheck={(_checked, info) => {
                  const key = String(info.node.key);
                  const branchKeys = menuBranchKeys(menuTree, key);
                  setSelectedKeys((current) => {
                    const next = new Set(current);
                    if (info.checked) {
                      branchKeys.forEach((item) => next.add(item));
                    } else {
                      // 同一实际页面的历史别名一并撤销，并移除祖先勾选，避免父级授权补回。
                      const removedRoutes = new Set(branchKeys.map(normalizeWorkspaceRoute));
                      menuTreeKeys(menuTree).filter((item) => removedRoutes.has(normalizeWorkspaceRoute(item))).forEach((item) => {
                        next.delete(item);
                        menuAncestorKeys(menuTree, item).forEach((ancestor) => next.delete(ancestor));
                      });
                    }
                    protectedKeys.forEach((item) => next.add(item));
                    return Array.from(next);
                  });
                }}
              />
            </div>
          </>
        )}
        {!snapshot && !loading && <Button onClick={() => setReloadKey((value) => value + 1)}>重新加载</Button>}
      </Spin>
    </Modal>
  );
}
