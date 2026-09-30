type PermissionMenu = {
  key: string;
  disabled?: boolean;
  link_url?: string;
  children?: PermissionMenu[];
};

export const PERMISSIONS_UPDATED_EVENT = "sunhold:permissions-updated";

export function notifyPermissionsUpdated() {
  window.dispatchEvent(new Event(PERMISSIONS_UPDATED_EVENT));
}

export function resolveGrantedMenuRoute(
  requested: string,
  menus: PermissionMenu[],
  grantedKeys: ReadonlySet<string>,
): string {
  if (grantedKeys.has(requested)) return requested;

  const findMenu = (items: PermissionMenu[]): PermissionMenu | undefined => {
    for (const item of items) {
      if (item.key === requested) return item;
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
        return item.key;
      }
    }
    return undefined;
  };

  // 父目录只负责进入已授权子页，不补授父目录或其他子页的权限。
  const parent = findMenu(menus);
  if (!parent?.children?.length || parent.disabled || parent.link_url) return requested;
  return firstGrantedLeaf(parent.children) || requested;
}
