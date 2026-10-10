import { dashboardWorkspace } from "./dashboardWorkspace";
import { FEEDBACK_ROUTE } from "./feedback/navigation";

type PermissionMenu = {
  key: string;
  disabled?: boolean;
  link_url?: string;
  children?: PermissionMenu[];
};

export const PERMISSIONS_UPDATED_EVENT = "sunhold:permissions-updated";
export const PERMISSIONS_UPDATED_STORAGE_KEY = "sunhold:permissions-updated-at";

const legacyRouteAliases: Record<string, string> = {
  "agent-document": "documents-agent",
  "system-parameters-notary-office": "system-parameters-notary",
  "system-users": "hr-all",
};

export function normalizeWorkspaceRoute(route: string): string {
  return legacyRouteAliases[route] || route;
}

export function notifyPermissionsUpdated() {
  localStorage.setItem(PERMISSIONS_UPDATED_STORAGE_KEY, String(Date.now()));
  window.dispatchEvent(new Event(PERMISSIONS_UPDATED_EVENT));
}

export function isWorkspaceRouteGranted(
  route: string,
  grantedKeys: ReadonlySet<string>,
  administrator = false,
): boolean {
  route = normalizeWorkspaceRoute(route);
  if (administrator || route === "dashboard" || route === FEEDBACK_ROUTE || grantedKeys.has(route)) return true;
  const hasFamily = (...prefixes: string[]) => Array.from(grantedKeys).some((key) =>
    prefixes.some((prefix) => key === prefix || key.startsWith(`${prefix}-`)),
  );
  const hasCaseRead = () => hasFamily("case-mine", "case-dept", "case-company", "case-archive");
  // 详情和控制台队列沿用对应业务页授权，不把组件使用的父路由当作额外授权。
  if (route === "case-global-search" || route.startsWith("case-detail-")) return hasCaseRead();
  if (route === "case-agent-center") return hasFamily("case");
  if (route.startsWith("customer-detail-")) return hasFamily("customer");
  if (["contract-detail-", "contract-change-", "contract-payment-apply-", "contract-invoice-apply-", "contract-investigation-"].some((prefix) => route.startsWith(prefix))) {
    return hasFamily("contract");
  }
  if (route.startsWith("finance-incoming-payment-")) return hasFamily("finance-incoming-company");
  const workspace = dashboardWorkspace(route);
  if (workspace?.kind === "case") return hasCaseRead();
  if (workspace?.kind === "receivable") return hasFamily("contract-receivable");
  if (workspace?.kind === "finance") {
    return workspace.view === "finance-refund" ? hasFamily("finance-refund") : hasFamily("finance-fee-query");
  }
  return false;
}

export function resolveGrantedMenuRoute(
  requested: string,
  menus: PermissionMenu[],
  grantedKeys: ReadonlySet<string>,
  administrator = false,
): string {
  const route = normalizeWorkspaceRoute(requested);
  if (isWorkspaceRouteGranted(route, grantedKeys, administrator)) return route;

  const findMenu = (items: PermissionMenu[]): PermissionMenu | undefined => {
    for (const item of items) {
      if (normalizeWorkspaceRoute(item.key) === route) return item;
      const child = findMenu(item.children || []);
      if (child) return child;
    }
    return undefined;
  };
  const firstGrantedLeaf = (items: PermissionMenu[]): string | undefined => {
    for (const item of items) {
      if (item.disabled || item.link_url) continue;
      if (item.children?.length) {
        const child = firstGrantedLeaf(item.children);
        if (child) return child;
      } else if (grantedKeys.has(item.key)) {
        return normalizeWorkspaceRoute(item.key);
      }
    }
    return undefined;
  };

  // 父目录只负责进入已授权子页，不补授父目录或其他子页的权限。
  const parent = findMenu(menus);
  if (parent?.children?.length && !parent.disabled && !parent.link_url) {
    const child = firstGrantedLeaf(parent.children);
    if (child) return child;
  }
  // 未批准的页面不能进入工作区，旧链接统一回到控制台。
  return "dashboard";
}
