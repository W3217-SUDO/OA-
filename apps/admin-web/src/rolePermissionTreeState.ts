// BUG20261104006（501310，范雨星 11-04）：角色权限树是严格模式（父子不联动），大类的勾不跟下面的页面走：
// 下面页面勾着时大类显示为空，看起来像“没勾任何权限”；勾了大类再取消下面页面，大类照样保存，后端按大类放开全部页面。
// 这里按下面的页面算大类的显示（全勾 / 半勾 / 空），保存时去掉没全勾的大类。只看页面（menu:），功能（action:）不影响大类。

export type PermissionTreeNode = { key: string | number; children?: PermissionTreeNode[] };

const isMenu = (key: string) => key.startsWith("menu:");

/** 节点下面所有“末级页面”（自己下面没有页面的 menu: 节点）。 */
function leafMenus(node: PermissionTreeNode): string[] {
  const result: string[] = [];
  const visit = (items: PermissionTreeNode[] = []) => items.forEach((child) => {
    if (isMenu(String(child.key)) && !hasMenuBelow(child)) result.push(String(child.key));
    visit(child.children);
  });
  visit(node.children);
  return result;
}

function hasMenuBelow(node: PermissionTreeNode): boolean {
  return (node.children || []).some((child) => isMenu(String(child.key)) || hasMenuBelow(child));
}

/** 树的显示：有下级页面的大类按下级页面算全勾、半勾或空；其余节点照选中状态。 */
export function menuTreeCheckState(tree: PermissionTreeNode[], selected: readonly string[]) {
  const chosen = new Set(selected);
  const checked = new Set(selected);
  const halfChecked = new Set<string>();
  const visit = (items: PermissionTreeNode[] = []) => items.forEach((node) => {
    const key = String(node.key);
    if (isMenu(key) && hasMenuBelow(node)) {
      const leaves = leafMenus(node);
      const ticked = leaves.filter((leaf) => chosen.has(leaf)).length;
      checked.delete(key);
      if (leaves.length && ticked === leaves.length) checked.add(key);
      else if (ticked) halfChecked.add(key);
    }
    visit(node.children);
  });
  visit(tree);
  return { checked: Array.from(checked), halfChecked: Array.from(halfChecked) };
}

/** 保存前去掉没有全勾的大类，避免后端把大类当成“下面全部开放”。 */
export function dropPartialParentMenus(tree: PermissionTreeNode[], selected: readonly string[]): string[] {
  const chosen = new Set(selected);
  const drop = new Set<string>();
  const visit = (items: PermissionTreeNode[] = []) => items.forEach((node) => {
    const key = String(node.key);
    if (isMenu(key) && hasMenuBelow(node) && !leafMenus(node).every((leaf) => chosen.has(leaf))) drop.add(key);
    visit(node.children);
  });
  visit(tree);
  return selected.filter((key) => !drop.has(key));
}
